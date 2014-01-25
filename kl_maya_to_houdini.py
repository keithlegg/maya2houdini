"""
My first Maya API project
Maya To Houdini Polygon and Scene Graph Animation Exporter
Keith Legg july 31,2008

translates polygon meshes as houdini geo (ascii)
animation as houdini chan files
and scenegraphs as a sourcable hscript

"""

##################################

import math, sys,re
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import maya.OpenMayaAnim as OpenMayaAnim


##################################



kPluginTranslatorTypeName ='HoudiniV9X' #name of maya translator plugin
fileextention             ='hs'         #name of script file extention

##################################
#EXPORT SETTINGS
#DEBUG THIS IS THE ANIMATION TIME RANGE
STARTFRAME = 0
ENDFRAME   = 200
#DEBUG NOT WORKING YET LEAVE SET TO SHORT
NAMEMODE   ='short' #long or short

##################################

"""
gets parenting info and iterates nodes
I couldnt figure out all of Maya's iterators so I built my own
"""
class kl_dag_info:

	def __init__(self):
				#
				self.TREE      = []
				self.TREENAMES = []	
				self.TREEMOBJ  = []	
				
	def reset(self):
				self.TREE      = []
				self.TREENAMES = []
				self.TREEMOBJ  = []	
				
	def getParentingInfo(self,node,mode):
		OUTDATA = []
		MFNDAGG = OpenMaya.MFnDagNode(node)
		
		if mode =='children':
				numkids = MFNDAGG.childCount()
				for i in range(numkids):
						child = MFNDAGG.child(i)
						OUTDATA.append(child)
				return OUTDATA
					
		if mode =='parents':
				numparents = MFNDAGG.parentCount()
				for i in range(numparents):
						parnam = MFNDAGG.parent(i)
						OUTDATA.append(parnam)
				if numparents==0:
						OUTDATA=None
				return OUTDATA
				
    #MFNDAGNODE
		if mode =='childrecurse':
				numkids = node.childCount()
				children =[]
				self.TREENAMES.append( node.fullPathName() )
				self.TREE.append( node )
				for i in range(numkids) :
						tempobj = node.child(i)
						dagobj = OpenMaya.MFnDagNode(tempobj)
						children.append( dagobj )
				for kid in children:
						self.getParentingInfo(kid,'childrecurse')
    #MOBJECT
		if mode =='childrecursemobj':
				cvtdgnode = OpenMaya.MFnDagNode(node)
				numkids = cvtdgnode.childCount()
				children =[]
				self.TREEMOBJ.append(node)
				for i in range(numkids) :
						tempobj = cvtdgnode.child(i)
						children.append( tempobj )
				for kid in children:
						self.getParentingInfo(kid,'childrecursemobj')
            						
##################################

def radian_to_degree(radians):
  outdegrees = 0.0
  outdegrees = (float (radians) / (3.14159265  )  )*180
  return outdegrees

######################
def degree_to_radians(degrees):
  outradians = 0.0
  outradians = float( degrees )*(180/3.14159265 )
  return outradians

##################################
"""
converts | to _ so maya's full-pathnames may be used
"""
def cleanMayaLongName(name):
		temp= ''
		if not name:
				return ''
		temp=name.replace('|','_')
		if temp[0]=='_':
				temp =temp[1:]
		length = len(temp)
		if temp[length-1]=='_':
				temp =temp[:-1]
		return temp
##################################
"""
handy little name text from Mobject
"""
def getNameFrMobject(obj):
			dagNode = OpenMaya.MFnDagNode(obj)
			dagPath = dagNode.fullPathName()
			return dagPath
##################################
"""
clips all but last name in path
example '/a/b/c/d' would be returned as '/a/b/c'
"""
def getnameprefix(fullName):
 			tempp = fullName.split('/')
			SHORTNAME =tempp[1]
			size = len(tempp)
			OUTPUTPATHNAME = ''
			count =0
			for temppp in tempp:
				if count <= (size-2):
							OUTPUTPATHNAME=OUTPUTPATHNAME+(temppp+'/')
				count =count+1
			return OUTPUTPATHNAME
      	
##################################
"""
creates a houdini .geo mesh file
"""
def OutputMesh(obj,outfilepath):
	TEXTDATA = []
	if obj.hasFn(OpenMaya.MFn.kMesh)==0:
			print 'NO MESH FOUND '
	if obj.hasFn(OpenMaya.MFn.kMesh):
		MESHNODE = OpenMaya.MFnMesh(obj)
		TEXTDATA.append ('PGEOMETRY V5\n')
		numverts = str(MESHNODE.numVertices() )
		TEXTDATA.append ('NPoints '+numverts+' '+'NPrims '+str(MESHNODE.numPolygons())+'\n')
		TEXTDATA.append ('NPointGroups 0 NPrimGroups 0\n')
		TEXTDATA.append ('NPointAttrib 0 NVertexAttrib 0 NPrimAttrib 0 NAttrib 0\n')
		#iterate and get verticies##########
		itGeom = OpenMaya.MItMeshVertex( obj )
		while not itGeom.isDone() :
				ITEM = itGeom.currentItem()
				dagNode = OpenMaya.MFnDagNode(obj)
				dagPath = dagNode.fullPathName()
				point = OpenMaya.MPoint( itGeom.position() )
				TEXTDATA.append(str(point.x) + ' '+str(point.y) + ' '+ str(point.z)  + ' 1 \n')#not sure what 1 is
				itGeom.next();
		TEXTDATA.append ('Run '+str(MESHNODE.numPolygons())+' Poly\n')	
		#iterate and get faces##########
		itMeshPoly = OpenMaya.MItMeshPolygon( obj )
		while not itMeshPoly.isDone() :
				CURPOLY = itMeshPoly.currentItem()
		   		NUMVERTSFACE = itMeshPoly.polygonVertexCount()
				vbuffer = ''
				itMeshPoly.vertexIndex(0)
				vbuffer = (' '+str(NUMVERTSFACE)+' < ')
				for a in ( range(NUMVERTSFACE) ):
		 			vbuffer=vbuffer+( str(itMeshPoly.vertexIndex(a) )+' '  )
					a=a+1
				vbuffer=vbuffer+'\n'
				TEXTDATA.append(vbuffer)
				itMeshPoly.next();
		########
		TEXTDATA.append ('beginExtra\n')
		TEXTDATA.append ('endExtra\n')
		
		#DEBUG
		outfilepath = 'C:'
		
		fileHandle = open((outfilepath+'/'+MESHNODE.name()+'.geo'),"w")
		for line in TEXTDATA:
				fileHandle.write(line)
		fileHandle.close()
						########
		return TEXTDATA
################
"""
Basically "bakes" the values for each frame
"""
def OutputAnimationData(obj,outfilepath,sf,ef):
			dagNode = OpenMaya.MFnDagNode(obj)
			dagPath = dagNode.fullPathName()
			
			namefix = cleanMayaLongName(dagPath[1:] )
			
			outfilepath = 'C://' #DEBUG DEBUG
			
			
			fHandle = open((outfilepath+'/'+namefix+'.chan'),"w")
			MANIM = OpenMayaAnim.MAnimControl()
			for i in range(sf,ef):
					MANIM.setCurrentTime(OpenMaya.MTime(i))
					fn = OpenMaya.MFnTransform(obj)
					
					TRANSLATION = fn.getTranslation(0)
					oiler = OpenMaya.MEulerRotation()
					ROTATION    = fn.getRotation(oiler)
					ROTVEC= OpenMaya.MVector( oiler.asVector() )
					line=(str(TRANSLATION[0])+' '+str(TRANSLATION[1])+' '+str(TRANSLATION[2])+' '+ str(radian_to_degree(ROTVEC[0]))+' '+str(radian_to_degree(ROTVEC[1]))+' '+str(radian_to_degree(ROTVEC[2])) +'\n' )
					fHandle.write(line)
			fHandle.close()		
			MANIM.setCurrentTime(OpenMaya.MTime(0))
			
################

"""
creates hscript to load nodes into houdini
if a mesh or camera is present it loads it automatically
"""
def mayaToHoudiniExportGroupMesh(meshpath,node,translate,rotate):
		out =[]
		NODNAM= getNameFrMobject(node)
		ROOT_HOU_PATH ='/obj'
		out.append( '\n' )
		out.append( 'opcd '+ROOT_HOU_PATH+'\n' )
		out.append( ("opadd -n geo "+ cleanMayaLongName(NODNAM) )+'\n' )
		KLDAG = kl_dag_info()
		children =KLDAG.getParentingInfo(node,'children')
		if children:
					for tmpnod in children:
							if tmpnod.hasFn(OpenMaya.MFn.kMesh):
									tmpdagfn = OpenMaya.MFnDagNode(tmpnod)
									out.append( ("opcd  "+cleanMayaLongName(NODNAM)+"\n" ))
									out.append( "opadd file "  +'\n')
									out.append( ("opparm file1 file  "+meshpath +'\n' )   )
									out.append( ("opcd  ..\n" ))

							if tmpnod.hasFn(OpenMaya.MFn.kCamera):
									print 'HAS CAMERA DUDE'							
									tmpdagfn = OpenMaya.MFnDagNode(tmpnod)
									out.append( "opadd -n cam "+ (cleanMayaLongName(NODNAM)+'cam') +'\n')
									parent =KLDAG.getParentingInfo(node,'parents')
									if parent:
												if cleanMayaLongName(NODNAM):
																	out.append( 'opwire '+ (cleanMayaLongName(NODNAM)+' '+(cleanMayaLongName(NODNAM)+'cam') +'\n') )
									out.append( "opcd "+(cleanMayaLongName(NODNAM)+'cam')+"\n")
									out.append( "opadd file cammodel\n")
									out.append( "opparm cammodel file ( defcam.bgeo )\n")
									out.append( "opcd ..\n")

									
		parent =KLDAG.getParentingInfo(node,'parents')
		if parent:
					parentname = getNameFrMobject(parent[0])
					if cleanMayaLongName(parentname):				
							out.append("opwire "+ cleanMayaLongName(parentname)+" "+ cleanMayaLongName(getNameFrMobject(node))+'\n' )	
							
		out.append("opparm "+ cleanMayaLongName(NODNAM) + " t (" +str(translate[0]) +" "+str(translate[1]) +" "+str(translate[2])+')\n')
		out.append("opparm "+ cleanMayaLongName(NODNAM) + " r (" +str(rotate[0])    +" "+str(rotate[1] )   +" "+str(rotate[2])+')\n')
		#wire up animation
		ANIMUTIL = OpenMayaAnim.MAnimUtil() #dagNode
		if ANIMUTIL.isAnimated(node):	
				out.append( "#import animation \n" )		
				out.append( ("opcd  "+cleanMayaLongName(NODNAM)  +'\n') )
				#USEDIR = meshpath[lenDIR-2)
				out.append( "chblockbegin\n" )
				out.append( "chadd  "+(ROOT_HOU_PATH+'/'+cleanMayaLongName(NODNAM))+" tx ty tz rx ry rz \n" )
				out.append( ("chkey -t 0 -v 0 -m 0 -A 0 -F '$F' "+(ROOT_HOU_PATH+'/'+cleanMayaLongName(NODNAM))+"\n" ) )
				out.append( "chblockend\n" )
				#out.append( ("opset -S on "+cleanMayaLongName(NODNAM)+ "\n" )   )
				#make the channel
				
				
				#read it in
				out.append( 'chread tx ty tz rx ry rz -f 0 13  '+(getnameprefix(meshpath)+cleanMayaLongName(NODNAM)+'.chan ')  +'\n')
        				
		return out
################
"""
creates hscript to load nodes into houdini
"""
def mayaToHoudiniExportGroup(channelpath,node,translate,rotate):
		out =[]
		ROOT_HOU_PATH ='/obj'
		NODNAM= getNameFrMobject(node)
		out.append( '\n' )
		out.append( 'opcd /obj\n' )
		out.append( ("opadd -n geo "+ cleanMayaLongName(NODNAM) )+'\n' )
		KLDAG = kl_dag_info()
		children =KLDAG.getParentingInfo(node,'children')
		parent =KLDAG.getParentingInfo(node,'parents')
		if parent:
					parentname = getNameFrMobject(parent[0])
					if cleanMayaLongName(getNameFrMobject(node)):
							if cleanMayaLongName(parentname):					
										out.append("opwire "+ cleanMayaLongName(parentname)+" "+ cleanMayaLongName(getNameFrMobject(node))+'\n' )		
							
		out.append("opparm "+ cleanMayaLongName(NODNAM) + " t (" +str(translate[0]) +" "+str(translate[1]) +" "+str(translate[2])+')\n')
		out.append("opparm "+ cleanMayaLongName(NODNAM) + " r (" +str(rotate[0])    +" "+str(rotate[1] )   +" "+str(rotate[2])+')\n')
		#wire up animation
		ANIMUTIL = OpenMayaAnim.MAnimUtil() #dagNode
		if ANIMUTIL.isAnimated(node):	
				out.append( "#import animation \n" )		
				out.append( ("opcd  "+cleanMayaLongName(NODNAM)  +'\n') )
				#USEDIR = meshpath[lenDIR-2)
				out.append( "chblockbegin\n" )
				out.append( "chadd  "+(ROOT_HOU_PATH+'/'+cleanMayaLongName(NODNAM))+" tx ty tz rx ry rz \n" )
				out.append( ("chkey -t 0 -v 0 -m 0 -A 0 -F '$F' "+(ROOT_HOU_PATH+'/'+cleanMayaLongName(NODNAM))+"\n" ) )
				out.append( "chblockend\n" )
				#out.append( ("opset -S on "+cleanMayaLongName(NODNAM)+ "\n" )   )
				#make the channel
				
				
				#read it in
				out.append( 'chread tx ty tz rx ry rz -f 0 13  '+(getnameprefix(channelpath)+cleanMayaLongName(NODNAM)+'.chan ')  +'\n')    		
		return out
		

################
"""
gets transfrom info (no scale yet)
"""

def OutputTransform(obj,mode):
	output = []
	if obj.hasFn(OpenMaya.MFn.kTransform)==0:
			print 'ERROR NO XFORM DETECTED'
	if obj.hasFn(OpenMaya.MFn.kTransform):
			XFORMNODE = OpenMaya.MFnTransform(obj)
			TRANSLATION = XFORMNODE.getTranslation(0)
			#TRANSLATION
			if mode =='t':
				output.append( TRANSLATION[0]  )
				output.append( TRANSLATION[1]  )
				output.append( TRANSLATION[2]   )
			###ROTATION
			if mode =='r':
				oiler = OpenMaya.MEulerRotation()
				ROTATION    = XFORMNODE.getRotation(oiler)
				ROTVEC= OpenMaya.MVector( oiler.asVector() )
				output.append(radian_to_degree(ROTVEC[0]) )
				output.append(radian_to_degree(ROTVEC[1]) )
				output.append(radian_to_degree(ROTVEC[2]) )
	return output
################
"""
not finished yet
"""

def OutputCamera(obj):
  TEXTDATA = []
  if obj.hasFn(OpenMaya.MFn.kCamera)==0:
       #TEXTDATA.append('no xform detected\n')
       pass
  if obj.hasFn(OpenMaya.MFn.kCamera):
        print 'debug obj is camera'

  return TEXTDATA	
################
"""
the actual translator code for Maya, this calls all the other functions
"""

class customNodeTranslator(OpenMayaMPx.MPxFileTranslator):
	def __init__(self):
		OpenMayaMPx.MPxFileTranslator.__init__(self)
	def haveWriteMethod(self):
		return True
	def haveReadMethod(self):
		return True
	def filter(self):
		return ('*.'+fileextention)
	def defaultExtension(self):
		return fileextention
	def writer( self, fileObject, optionString, accessMode ):
		#
		try:
			fullName = fileObject.fullName()
			tempp = fullName.split('/')
			SHORTNAME =tempp[1]
			size = len(tempp)
			OUTPUTPATHNAME = ''
			count =0
			for temppp in tempp:
				if count <= (size-2):
							OUTPUTPATHNAME=OUTPUTPATHNAME+(temppp+'/')
				count =count+1
			BUFFERLINE = ''
			MESHESTOEXPORT   = []
			CHANNELSTOEXPORT = []
			CAMERASTOEXPORT  = []
			CURVESTOEXPORT   = []
			#NURBSTOEXPORT    = []
			#################
			DAGIT = OpenMaya.MItDag( OpenMaya.MItDag.kDepthFirst )
	
			KLDAGGER = kl_dag_info()
			KLDAGGER.reset()
									
			while not DAGIT.isDone():
					MFNDAGNODE = OpenMaya.MFnDagNode( DAGIT.currentItem() )   #MFNDAGNODE
					MOBJECT = DAGIT.currentItem()
					DAGPATH = MFNDAGNODE.fullPathName()

					#ONLY ITERATE ROOT NODES, THEN RUN MY OWN ITERATOR ON EACH ROOTNODE
					if DAGIT.depth() ==1:
							if checkOmittedNodes(DAGPATH):
									KLDAGGER.getParentingInfo(MOBJECT,'childrecursemobj')
									
					DAGIT.next()

			#################

			#SORT THE TYPES OF NODES TO EXPORT
			for CHMOBJ in  KLDAGGER.TREEMOBJ:
					MFNDAGNODE = OpenMaya.MFnDagNode( CHMOBJ )
					if CHMOBJ.hasFn(OpenMaya.MFn.kTransform):
							MANIM = OpenMayaAnim.MAnimUtil() #dagNode
							if MANIM.isAnimated(CHMOBJ):
									CHANNELSTOEXPORT.append([CHMOBJ,('/'+SHORTNAME+'/') ]) #store mobject and name
							#if not MANIM.isAnimated(CHMOBJ):
							#			OutputTransform(CHMOBJ)
					#EXPORT MESHES							
					if CHMOBJ.hasFn(OpenMaya.MFn.kMesh):
							if NAMEMODE =='short':
										MESHESTOEXPORT.append([CHMOBJ,('/'+SHORTNAME+'/') ])  #store mobject and name		
							if NAMEMODE =='long':
										MESHESTOEXPORT.append([CHMOBJ,((OUTPUTPATHNAME+cleanMayaLongName(DAGPATH)) ) ])  #store mobject and name		
			#export the geometry,animation and scenegraph         			
			#######			
			for mesh in MESHESTOEXPORT:
						OutputMesh(mesh[0],mesh[1])
			for chan in CHANNELSTOEXPORT:
						OutputAnimationData(chan[0],chan[1],STARTFRAME,ENDFRAME)#hard coded times at the moment
			#EXPORT SCENEGRAPH
			HSCRIPTTEXT = []
		
			for MOBJNODE in KLDAGGER.TREEMOBJ:
					MFNDAGNODE = OpenMaya.MFnDagNode( MOBJNODE )
					if MOBJNODE.hasFn(OpenMaya.MFn.kTransform):
							nodname = MFNDAGNODE.fullPathName()
							fixname = cleanMayaLongName(nodname)
							TRANSLATION = OutputTransform(MOBJNODE,'t')
							ROTATION    = OutputTransform(MOBJNODE,'r')
							#determine if mesh exists
							DAGWOOD = kl_dag_info()
							checkmesh = DAGWOOD.getParentingInfo(MOBJNODE,'children')
							meshexists = 0
							for tmpnode in checkmesh:
										if tmpnode.hasFn(OpenMaya.MFn.kMesh) or tmpnode.hasFn(OpenMaya.MFn.kCamera):
														meshexists=meshexists+1
														meshname = getNameFrMobject(tmpnode)
														fooo=meshname.split('|')
														nameend = fooo[len(fooo)-1]				
							if meshexists>0:
												BUFFER= mayaToHoudiniExportGroupMesh((OUTPUTPATHNAME+nameend+'.geo' ),MOBJNODE,TRANSLATION,ROTATION)	
                        					
							if meshexists==0:
												BUFFER= mayaToHoudiniExportGroup(OUTPUTPATHNAME,MOBJNODE,TRANSLATION,ROTATION)
							for line in BUFFER:
									HSCRIPTTEXT.append(line)

			#WRITE TO FILE
			print 'WRITING FILE ' +fullName
			scriptfile = open(fullName,"w")
			for templine in HSCRIPTTEXT :
						scriptfile.write(templine)
			scriptfile.close()
    			
		except:
			sys.stderr.write( "Failed to write file information\n")
			raise
		#			
	def processLine( self, lineStr ):
	  #place holder , no import currently implemented
		print "read <%s>" % lineStr
		#		
	def reader( self, fileObject, optionString, accessMode ):
		try:
			fullName = fileObject.fullName()
			fileHandle = open(fullName,"r")
			for line in fileHandle:
				self.processLine( line )
			fileHandle.close()
		except:
			sys.stderr.write( "Failed to read file information\n")
			raise



################
"""
a list of nodes to omit , a bad way to do it but it was easy
"""
def checkOmittedNodes(node):
  array = []
  array.append('|groundPlane_transform')
  array.append('|ViewCompass'  )
  array.append('|Manipulator1' )
  array.append('|UniversalManip' )
  array.append('|persp'  )
  array.append('|top'  )
  array.append('|front' )
  array.append('|side'   )
  array.append('|UniversalManip1' )
  array.append('|groundPlane_transform|groundPlane' )
  array.append('|persp|perspShape'  )
  array.append('|top|topShape'  )
  array.append('|front|frontShape')
  array.append('|side|sideShape' )
  ###
  for wack in array:
     if wack == node:
        return 0
  return 1







# creator
def translatorCreator():
	return OpenMayaMPx.asMPxPtr( customNodeTranslator() )

# initialize the script plug-in
def initializePlugin(mobject):
	mplugin = OpenMayaMPx.MFnPlugin(mobject)
	try:
		mplugin.registerFileTranslator( kPluginTranslatorTypeName, None, translatorCreator )
	except:
		sys.stderr.write( "Failed to register translator: %s" % kPluginTranslatorTypeName )
		raise

# uninitialize the script plug-in
def uninitializePlugin(mobject):
	mplugin = OpenMayaMPx.MFnPlugin(mobject)
	try:
		mplugin.deregisterFileTranslator( kPluginTranslatorTypeName )
	except:
		sys.stderr.write( "Failed to deregister translator: %s" % kPluginTranslatorTypeName )
		raise

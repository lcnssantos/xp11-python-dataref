from XPLMDefs import *
from XPLMMenus import *
from XPLMUtilities import *
from XPLMProcessing import *
from XPLMDataAccess  import * 
import json
import socket


class PythonInterface:

	def StartTCPServer(self):
		
		try: 
			socket.setdefaulttimeout(0.01)

			self.tcp = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

			orig = ('',int(self.config["port"]))

			self.tcp.bind(orig)
			self.tcp.listen(1)

			print("Start server at port "+self.config["port"])

			self.ServerActionsCB = self.ServerActionsCallback
			self.FlightLoopCB = self.FlightLoopCallback

			XPLMRegisterFlightLoopCallback(self,self.ServerActionsCB,1.0,0)
			XPLMRegisterFlightLoopCallback(self,self.FlightLoopCB,0.5,0)

			self.ServerRunning = True

			XPLMEnableMenuItem(self.myMenu,self.StopItem,1)
			XPLMEnableMenuItem(self.myMenu,self.StartItem,0)
		except Exception, e:
			print("Error to start server at port "+self.config["port"]+ ' '+str(e))
		pass

	def CloseTCPServer(self):
		print('Server stopped ad port '+self.config["port"])

		XPLMUnregisterFlightLoopCallback(self, self.ServerActionsCB, 0)
		XPLMUnregisterFlightLoopCallback(self,self.FlightLoopCB,0)


		self.ServerRunning = False
		XPLMEnableMenuItem(self.myMenu,self.StopItem,0)
		XPLMEnableMenuItem(self.myMenu,self.StartItem,1)


		pass

	def XPluginStart(self):
		self.Name = "X-Virtual Copilot"
		self.Sig =  "ToFlySim.Python.XVirtualCopilot"
		self.Desc = "A network interface to handle datarefs"

		self.ServerRunning = False
		self.ClientConnected = False
		self.ServerActionsInterval = 0.2

		self.stack = []
		self.stackCounter = 0

		self.mySubMenuItem = XPLMAppendMenuItem(XPLMFindPluginsMenu(), "XvirtualCopilot", 0, 1)
		
		self.MyMenuHandlerCB = self.MyMenuHandlerCallback
		self.myMenu = XPLMCreateMenu(self, "XVirtualCopilot", XPLMFindPluginsMenu(), self.mySubMenuItem, self.MyMenuHandlerCB,	0)

		self.StartItem = XPLMAppendMenuItem(self.myMenu, "Start Server", 0, 1)
		self.StopItem = XPLMAppendMenuItem(self.myMenu, "Stop Server", 1, 1)

		XPLMEnableMenuItem(self.myMenu,self.StopItem,0)

		self.GetConfig()

		self.StartTCPServer()

		return self.Name, self.Sig, self.Desc

	def XPluginStop(self):
		
		XPLMDestroyMenu(self, self.myMenu)
		XPLMRemoveMenuItem(XPLMFindPluginsMenu(),self.mySubMenuItem)

		if(self.ServerRunning):
			self.CloseTCPServer()

		pass

	def XPluginEnable(self):
		return 1

	def XPluginDisable(self):
		pass

	def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
		pass

	def MyMenuHandlerCallback(self, inMenuRef, inItemRef):
		
		if (inItemRef == 0) :
			self.StartTCPServer()
		else:
			self.CloseTCPServer()
		pass

	def ServerActionsCallback(self, elapsedMe, elapsedSim, counter, refcon):

		if not (self.ClientConnected):
			try:
				self.conn, self.client = self.tcp.accept()
				print('New client connected')
				self.ClientConnected = True
			except:
				return self.ServerActionsInterval
		else:	
			try:
				msg = self.conn.recv(1024)

				if not msg:
					print("Client disconnected")
					self.ClientConnected = False

				else:
					self.AddMessage(msg)	
			except:
				return self.ServerActionsInterval
		return self.ServerActionsInterval

	def FlightLoopCallback(self,elapsedMe,elapsedSim,counter,refcon):

		self.stackCounter += 1

		if(self.stackCounter >= len(self.stack)):
			self.stackCounter = 0

		if(len(self.stack) > 0):
			self.ActualStackItem = self.stack[self.stackCounter]
			self.HandlerStack()


		return 1/(float(len(self.stack)+1))
	
	def GetConfig(self):
		path = XPLMGetSystemPath()+'Resources/plugins/PythonScripts/config.json'
		try:
			file = open(path,'r')
			self.config = json.loads(file.read())
			file.close()
		except: 
			print('Error to get Config file')
		pass

	def AddMessage(self,msg):
		self.stack.append(msg)
		pass

	def HandlerStack(self):
		StackItem = json.loads(self.ActualStackItem)

		if(StackItem['TYPE'] == "DATAREF"):
			self.HandlerDataref()
		if(StackItem['TYPE'] == "EVENT"):
			self.HandlerEvent()
		if(StackItem['TYPE'] == "REMOVE"):
			self.HandlerRemove()
		if(StackItem['TYPE'] == "COMMAND"):
			self.HandlerCommand()
		pass


	################## DATAREF HANDLERS ###############################

	def HandlerDataref(self):
		HandlerData = json.loads(self.ActualStackItem)
		
		Response = ''

		if(HandlerData['SUBTYPE'] == "SET"):
			self.SetDataref(HandlerData['DATAREF'],HandlerData['VALUE'])
			Response = {'ID': HandlerData['ID'], 'STATUS': 'OK'}

		elif(HandlerData['SUBTYPE'] == "GET"):
			Response = {'ID': HandlerData['ID'], 'STATUS': 'OK','VALUE': self.GetDataref(HandlerData['DATAREF'])}

		self.conn.send(str.encode(json.dumps(Response)))
		self.stack.remove(self.ActualStackItem)

		pass

	def GetDataref(self,dataref):		
		try:
			DatarefReference = XPLMFindDataRef(dataref)		
			DatarefType = XPLMGetDataRefTypes(DatarefReference)

			DatarefValue = 0

			if(DatarefType == xplmType_Unknown):
				print('Unkonwn')

			elif(DatarefType == xplmType_Int):
				DatarefValue = XPLMGetDatai(DatarefReference)

			elif(DatarefType == xplmType_Float):
				DatarefValue = XPLMGetDataf(DatarefReference)

			elif(DatarefType == xplmType_Double):
				DatarefValue = XPLMGetDatai(DatarefReference)

			elif(DatarefType == xplmType_FloatArray):
				print('Float Array')

			elif(DatarefType == xplmType_IntArray):
				print('Int Array')

			elif(DatarefType == xplmType_Data):

				print('Data')
		except:
			return DatarefValue
		
		return DatarefValue
	
	def SetDataref(self,dataref,value):	
		DatarefReference = XPLMFindDataRef(dataref)
		DatarefType = XPLMGetDataRefTypes(DatarefReference)

		if(DatarefType == xplmType_Unknown):
			print('Unkonwn')

		elif(DatarefType == xplmType_Int):
			XPLMSetDatai(DatarefReference,int(value))

		elif(DatarefType == xplmType_Float):
			XPLMSetDataf(DatarefReference,float(value))

		elif(DatarefType == xplmType_Double):
			XPLMSetDatai(DatarefReference,int(value))

		elif(DatarefType == xplmType_FloatArray):
			print('Float Array')

		elif(DatarefType == xplmType_IntArray):
			print('Int Array')

		elif(DatarefType == xplmType_Data):
			print('Data')
		
		pass


	################################################################

	################## COMMAND HANDLERS ############################
	def HandlerCommand(self):
		HandlerData = json.loads(self.ActualStackItem)
		Command = XPLMFindCommand(HandlerData["COMMAND"]);

		if(HandlerData["SUBTYPE"] == "once"):
			XPLMCommandOnce(Command)
		elif(HandlerData["SUBTYPE"] == "begin"):
			XPLMCommandBegin(Command)
		elif(HandlerData["SUBTYPE"] == "end"):
			XPLMCommandEnd(Command)

		
		Response = {'ID': HandlerData['ID'], 'STATUS': 'OK'}

		self.conn.send(str.encode(json.dumps(Response)))

		


		self.stack.remove(self.ActualStackItem);
		pass

	################################################################

	###################### EVENTS HANDLERS #########################

	def HandlerEvent(self):
		HandlerData = json.loads(self.ActualStackItem)

		Data1 = self.GetEventItemValue(HandlerData['DATA_1'])
		Data2 = self.GetEventItemValue(HandlerData['DATA_2'])

		if(HandlerData['OPERATION'] == "EQUAL" and Data1 == Data2):
			self.DispatchEvent(HandlerData)

		elif(HandlerData['OPERATION'] == "GREATER" and Data1 >= Data2):
			self.DispatchEvent(HandlerData)

		elif(HandlerData['OPERATION'] == "LESS" and Data1 <= Data2):
			self.DispatchEvent(HandlerData)
		
		pass

	def GetEventItemValue(self,item):
		
		A = item['A']
		B = item['B']

		itemType = item['TYPE']
		itemArgument = item['ARGUMENT']

		if(itemType == "DATAREF"):
			dataValue = float(self.GetDataref(itemArgument)) * float(A) + float(B)
		else:
			dataValue = float(itemArgument) * float(A) + float(B)

		return dataValue

	def DispatchEvent(self,HandlerData):
		Data = {'ID': HandlerData['ID'], 'TYPE': 'EVENT_DISPATCH'}

		self.conn.send(str.encode(json.dumps(Data)))

		if(HandlerData['REPEAT'] == "SINGLE"):
			self.stack.remove(self.ActualStackItem)
		pass
	
	###############################################################

	#################### REMOVE HANDLER ###########################
	def HandlerRemove(self):
		HandlerData = json.loads(self.ActualStackItem)

		for x in self.stack:
			stackItemData = json.loads(x)
			if(HandlerData['ID'] == stackItemData['ID']):
				self.stack.remove(x)
		pass
	
	#################################################################


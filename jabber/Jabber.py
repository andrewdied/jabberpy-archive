import XMLStream
from string import split,find,replace

False = 0;
True  = 1;


class Connection(XMLStream.Client):
    def __init__(self, host, port=5222, debug=True, log=False):
        self.msg_hdlr  = None
        self.pres_hdlr = None
        self.iq_hdlr   = None

        self._roster = {}
        self._agents = {}
        self._reg_info = {}
        self._reg_agent = ''
        
        self.lastErr = ''
        self.lastErrCode = 0

        XMLStream.Client.__init__(self, host, port, 'jabber:client', debug, log)

    def dispatch(self, root_node ):
        self.DEBUG("dispatch called")
        
        if root_node.tag == 'message':
            self.DEBUG("got message dispatch")
            type = None
            frm  = root_node.attrs['from']
            to   = root_node.attrs['to']
            if root_node.has_key('type'): type = root_node.attrs['type']
            body = ''
            for n in root_node.kids:
                if n.tag == 'body':
                    body = n.data
                if n.tag == 'error':
                    self.lastErr = n.data
                    self.lastErrCode = n.attrs['code']
                if n.tag == 'subject':
                    msg_obj.setSubject(n.data)
                    
            msg_obj = Message(to, body)
            msg_obj.setFrom(frm)
            msg_obj.setType(type)
            self.messageHandler(msg_obj)
            
        elif root_node.tag == 'presence':
            self.DEBUG("got presence dispatch")
            id     = None
            show   = None
            status = None
            priority = None
            type = None
            to = ''
            
            frm  = root_node.attrs['from']
        ##    to   = root_node.attrs[root_node.namespace+' to']
            if root_node.attrs.has_key('id'):
                id   = root_node.attrs['id']
            else:
                id = None
            if root_node.attrs.has_key('type'):
                type = root_node.attrs['type']
            for n in root_node.kids:
                if n.tag == 'show':
                    show = n.data
                if n.tag == 'status':
                    status = n.data
                if n.tag == 'priority':
                    priority = int(n.data)
                if n.tag == 'x': ## ToDO ##
                    pass

            pres_obj = Presence(to, type)
            pres_obj.setFrom(frm)
            if id: pres_obj.setID(id)
            if show: pres_obj.setShow(show)
            if status: pres_obj.setStatus(status)
            if priority: pres_obj.setPriority(priority)
            self.presenceHandler(pres_obj)

            
        elif root_node.tag == 'iq':
            ## Check for an error
            self.DEBUG("got an iq");
            iq_obj = Iq()
            if root_node.attrs.has_key('to'):
                iq_obj.setTo(root_node.attrs['to'])
            if root_node.attrs.has_key('type'):
                iq_obj.setType(root_node.attrs['type'])
            if root_node.attrs.has_key('from'):
                iq_obj.setFrom(root_node.attrs['from'])
            if root_node.attrs.has_key('id'):
                iq_obj.setID(root_node.attrs['id'])
            if root_node.kids:
                iq_obj.setKids(root_node.kids)
            
            if root_node.attrs['type'] == 'error':
                for n in root_node.kids:
                    if n.tag == 'error':
                        self.lastErr = n.data
                        self.lastErrCode = n.attrs['code']

            for n in root_node.kids:
                if n.tag == 'query':
                    ## Build roster ###
                    if n.namespace == 'jabber:iq:roster' \
                       and root_node.attrs['type'] == 'result':
                        self._roster = {}
                        for item in n.kids:
                            jid = None
                            name = None
                            sub = None
                            ask = None
                            if item.attrs.has_key('jid'):
                                jid = item.attrs['jid']
                            if item.attrs.has_key('name'):
                                name = item.attrs['name']
                            if item.attrs.has_key('subscription'):
                                sub = item.attrs['subscription']
                            if item.attrs.has_key('ask'):
                                ask = item.attrs['ask']
                            if jid:
                                self._roster[jid] = \
                                { 'name': name, 'ask': ask, 'subscription': sub }
                            else:
                                self.DEBUG("roster - jid not defined ?")
                        self.DEBUG("roster => %s" % self._roster)
                        
                    elif n.namespace == 'jabber:iq:register':
                        if root_node.attrs['type'] == 'result':
                            self._reg_info = {}
                            for item in n.kids:
                                data = None
                                if item.data: data = item.data
                                self._reg_info[item.tag] = data
                        else:
                            self.DEBUG("print type is %s" % root_node.attrs['type'])

                    elif n.namespace == 'jabber:iq:agents':
                        if root_node.attrs['type'] == 'result':
                            self.DEBUG("got agents result")
                            self._agents = {}
                            for agent in n.kids:
                                if agent.tag == 'agent': ## hmmm
                                    self._agents[agent.attrs['jid']] = {}
                                    for info in agent.kids:
                                        data = None
                                        if info.data: data = info.data
                                        self._agents[agent.attrs['jid']][info.tag] = data
                        

                    else:
                        pass
                    
            self.iqHandler(iq_obj)
            
        else:
            self.DEBUG("whats a tag -> " + root_node.tag)

    
    def auth(self,username,passwd,resource):
        str =  u"<iq type='set'>                    \
                <query xmlns='jabber:iq:auth'><username>%s</username><password>%s</password> \
                <resource>%s</resource></query></iq>" % ( username,passwd,resource )
        self.send(str)
        if (find(self.read(),'error') == -1):         ## this will fire off a callback for ok ? 
            return True
        else:
            return False

    def requestRoster(self):
        self.send(u"<iq type='get'><query xmlns='jabber:iq:roster'/></iq>")
        self._roster = {}
        while (not self._roster): self.process(0)
        
    def requestRegInfo(self,agent=''):
        if agent: agent = agent + '.'
        self.send(u"<iq type='get' to='%s%s'><query xmlns='jabber:iq:register'/></iq>" % ( agent ,self._host ))
        while (not self._reg_info): self.process(0)
        
    def send(self, what):
         self.DEBUG("type is %s " % type(what))
         if type(what) is type("") or type(what) is type(u""): ## Is it a string ?
             XMLStream.Client.write(self,what)
         else:       ## better add if isinstance(what, protocol_superclass) ..?
             XMLStream.Client.write(self,what.as_xml())

    def sendInitPresence(self):
        self.send("<presence/>");

    def setMessageHandler(self, func):
        self.msg_hdlr = func

    def setPresenceHandler(self, func):
        self.pres_hdlr = func

    def setIqHandler(self, func):
        self.iq_hdlr = func

    def getRoster(self):
        return self._roster
        # send request
        # do read
        # return internal roster hash

    def getRegInfo(self):
        return self._reg_info

    def setRegInfo(self,key,val):
        self._reg_info[key] = val

    def sendRegInfo(self, agent=''):
        if agent: agent = agent + '.'
        str =u'<iq type="set" to="' + agent + self._host + '"> \
               <query xmlns="jabber:iq:register">'
        for info in self._reg_info.keys():
            str = str + u"<%s>%s</%s>" % ( info, self._reg_info[info], info )
        str = str + u"</query></iq>"
        self.send(str)

    def requestAgents(self):
        agents_iq = Iq(type='get')
        agents_iq.setQueryNS('jabber:iq:agents')
        self.send(agents_iq)
        self._agents = {}
        while (not self._agents): self.process(0)
        return self._agents


    def messageHandler(self, msg_obj): ## Overide If You Want ##
        if self.msg_hdlr != None: self.msg_hdlr(self, msg_obj)
        
    def presenceHandler(self, pres_obj): ## Overide If You Want ##
        if self.pres_hdlr != None: self.pres_hdlr(self, pres_obj)

    def iqHandler(self, iq_obj): ## Overide If You Want ##
        if self.iq_hdlr != None: self.iq_hdlr(self, iq_obj)


#
# TODO:
# all the below structures should really just define there 'top level' tag.
# Tags inside this should really be an XMLStream Node as a .kids attr ?
# 
# The Iq object currently does this. Need to think more obout it
#



class Message:
    def __init__(self, to='', body=''):
        ##self.frm = 'mallum@jabber.com'
        self._to         = to
        self._body       = body
        self._frm       = None
        self._type       = None
        self._subject    = None
        self._thread     = None
        self._error      = None
        self._error_code = None
        self._timestamp  = None
        self._id         = None
        
    def getTo(self): return self._to
    def getFrom(self): return self._frm
    def getBody(self): return self._body
    def getType(self): return self._type
    def getSubject(self): return self._subject
    def getThread(self): return self._thread
    def getError(self): return self._error
    def getErrorCode(self): return self._error_code
    def getTimestamp(self): return self._timestamp
    def getID(self): return self._id

    def setTo(self,val): self._to = val
    def setFrom(self,val): self._frm = val
    def setBody(self,val): self._body = val
    def setType(self,val): self._type = val ## TODO: Define constants 
    def setSubject(self,val): self._subject = val
    def setThread(self,val): self._thread = val
    def setError(self,val): self._error = val
    def setErrorCode(self,val): self._error_code = val
    def setTimestamp(self,val): self._timestamp = val
    def setID(self,val): self._id = val
    
    def as_xml(self):
        s = "<message "
        if self._to:   s=s + "to='%s' " % self._to
        if self._type: s=s + "type='%s' " % self._type
        s=s + ">"
        if self._subject: s=s + "<subject>%s</subject>" % self._subject
        if self._body:    s=s + "<body>%s</body>" % self._body
        s=s + "</message>"
        return s

    def build_reply(self, reply_txt=''):
        return Message(self._frm, reply_txt)

class Presence:
    def __init__(self, to='', type=None):
        self._to = to
        self._frm = None
        self._type = type
        self._status = None
        self._show   = None
        self._priority = None
        self._id       = None
        
    def getTo(self):  return self._to
    def getFrom(self): return self._frm
    def getType(self):     return self._type
    def getStatus(self):   return self._status
    def getShow(self):     return self._show
    def getPriority(self): return self._priority
    def getID(self): return self._id

    def setTo(self,val):       self._to = val
    def setFrom(self,val):     self._frm = val
    def setType(self,val):     self._type = val
    def setStatus(self,val):   self._status = val
    def setShow(self,val):     self._show = val
    def setPriority(self,val): self._priority = val
    def setID(self,val):       self._id = val

    def as_xml(self):
        s = "<presence "
        if self._to:   s=s + "to='%s' " % self._to
        if self._type: s=s + "type='%s' " % self._type
        if self._id: s=s + "id='%s' " % self._id
        s=s + ">"
        if self._status: s=s + "<status>%s</status>" % self._subject
        if self._show:   s=s + "<show>%s</show>" % self._body
        if self._priority:   s=s + "<show>%s</show>" % self._priority
        s=s + "</presence>"
        return s


class Iq: 
    def __init__(self, to='', type=None):
        self._to = to
        self._frm = None
        self._type = type
        self._id   = None
        self._query = None ## holds query namespace ##
        self._kids  = None
        
    def getTo(self):  return self._to
    def getFrom(self): return self._frm
    def getType(self):     return self._type
    def getID(self): return self._id
    def getQueryNS(self): return self._query

    def setTo(self,val):       self._to = val
    def setFrom(self,val):     self._frm = val
    def setType(self,val):     self._type = val
    def setID(self,val):       self._id = val
    def setKids(self,val):     self._kids = val
    def setQueryNS(self,val):     self._query = val
    def as_xml(self):
        s = "<iq "
        if self._to:   s=s + "to='%s' " % self._to
        if self._type: s=s + "type='%s' " % self._type
        if self._id: s=s + "id='%s' " % self._id
        s=s + ">"
        if self._query: s=s + "<query xmlns='%s' />" % self._query
        s=s + "</iq>"
        return s













#!/usr/bin/env python3
#from xml.dom import minidom
import xml.etree.ElementTree as ElementTree
import xml.sax.saxutils
import re
import string
import time
import shelve
import random
import datetime
import math
import collections
import locale
import codecs

def static_var(varname, val):
  def decorate(fn):
    setattr(fn, varname, val)
    return fn
  return decorate

class AIMLParser:
  magic_words = {'topic' : '__TOPIC__',
                 'that' : '__THAT__',
                 'template' : '__TEMPLATE__',
                 'bot' : '__BOT__' }
  replacements = {'person': #Swap 1st & 3rd person
                    {
                    'I': 'he',  #1st -> 3rd person
                    'me': 'him',
                    'myself': 'himself',
                    'mine': 'his',
                    'my': 'his',

                    'we': 'they',
                    'us': 'them',
                    'ourselves': 'themselves',
                    'ours': 'theirs',
                    'our': 'their',

                    'he': 'I', #3rd -> 1st person
                    'him': 'me',
                    'himself': 'myself',
                    'hisself': 'myself',
                    'his': 'my',

                    'she': 'I', #3rd -> 1st person
                    'her': 'me',
                    'herself': 'myself',
                    'hers': 'my',

                    'it': 'I', #3rd -> 1st person
                    'itself': 'myself',
                    'its': 'my',

                    'one':'I',
                    'oneself':'myself',
                    'one\'s':'my',

                    'they':'we',
                    'them':'me',
                    'themselves':'myself',
                    'theirs':'mine',
                    'their':'my',
                    },
              'person2': {
                    'I': 'you',  #1st -> 2nd person
                    'me': 'you',
                    'myself': 'yourself',
                    'mine': 'yours',
                    'my': 'your',

                    'we': 'you',
                    'us': 'you',
                    'ourselves': 'yourselves',
                    'ours': 'yours',
                    'our': 'your',
                    },
              'gender': {
                    'he':'she',
                    'him':'her',
                    'himself':'herself',
                    'hisself':'herself',
                    'his':'her',

                    'she':'he',
                    'her':'him',
                    'herself':'himself',
              }
        }

  def __init__(self):
    self._topic = '*'
    self.aiml_graph = {}

  def __del__(self):
    def nullfn():
      pass
    getattr(self.aiml_graph, 'close', nullfn)()

  def parseString(self, s):
    self._parse(ElementTree.fromstring(s))

  def parse(self, buff):
    self._parse(ElementTree.parse(buff))

  def _parse(self, node):
    getattr(self, "parse_%s" % node.__class__.__name__)(node)

  def parse_ElementTree(self, node):
    self._parse(node.getroot())

  def parse_Text(self, node):
    return node.data
  
  def parse_Comment(self, node):
    pass

  def parse_Element(self, node):
    return getattr(self, "do_%s" % node.tag.lower())(node)

  @static_var('split_regex', re.compile(r'(<bot.*?\/>)|\s+'))
  def make_path(self, pattern):
    return [ tok.upper() for tok in self.make_path.split_regex.split(pattern) if tok != None]

  def innerText(self, node):
    return ElementTree.tostring(node).decode('utf-8', 'replace').strip()[2+len(node.tag):-(3+len(node.tag))]

  def do_aiml(self, node):
    for n in node:
        self._parse(n)

  def do_topic(self, node):
    self._topic = node.get('name', '*')
    for n in node:
      self._parse(n)
    self._topic = '*'

  def do_category(self, node):
    template = ElementTree.tostring(node.find('template')).decode('utf-8', 'replace')
    pattern = node.find('pattern')
    txt=self.innerText(pattern)
    pattern = self.make_path(txt)
    pattern.append(self.magic_words['that'])
    that = node.find('that')
    if that != None:
      pattern.extend(self.make_path(self.innerText(that)))
    else:
      pattern.append('*')
    pattern.append(self.magic_words['topic'])
    pattern.extend(self.make_path(self._topic))
    self.addToGraph(pattern, template)

  @static_var('bot_regex', re.compile(r'<bot\s*name="([^"]*)"\s*/>'))
  def addToGraph(self, path, template):
    root_node = self.aiml_graph.get(path[0], {})
    current_node = root_node
    for tok in path[1:]:
      if tok.startswith('<bot'):  #Seperate bot predicates
        current_node[self.magic_words['bot']] = current_node.get(self.magic_words['bot'], {})
        current_node = current_node[self.magic_words['bot']]
        tok = (self.addToGraph.bot_regex.search(tok).group(1))
      current_node[tok] = current_node.get(tok, {})
      current_node = current_node[tok]
    self.aiml_graph[path[0]] = root_node
    if self.magic_words['template'] in current_node:
      print('*** WARNING: Overwriting pattern', path, '*****')
    current_node[self.magic_words['template']] = template

class Brain:
  magic_words = {'topic' : '__TOPIC__',
                 'that' : '__THAT__',
                 'template' : '__TEMPLATE__',
                 'bot' : '__BOT__' }
  def __init__(self, brain_dict={}, bot={}):
    self.brain = brain_dict
    self.resp = collections.deque([], 10)
    self.bot = bot
    self.user = {}

  def saveBrain(self,filename):
    s = shelve.open(filename)
    for k in self.brain.keys():
      s[k] = self.brain[k]
    s.close()

  def loadBrain(self,filename):
    s = shelve.open(filename)
    for k in s.keys():
      self.brain[k] = s[k]
    s.close()

  def reply(self, msg, user=''):
    return self.match(msg, user, record=True)

  def match(self, inp, user, depth=0, record=False):
    self.user[user] = self.user.get(user, {}) #Allocate a new user if needed
    current_node = self.brain
    matches = []
    for s in self.normalize(inp):
      s = self.makeInputPath(s) + [self.magic_words['that'],'', self.magic_words['topic'],'']
      match = self._match(s)
      if match == None: continue
      matches.append(match)
    sentences = []
    for m in matches:
      if len(m) == 0: continue
      sentences.append(self.respond(m, ElementTree.fromstring(m[-1]), user, depth))
    if record:
      self.resp.append((inp, sentences))
    return ' '.join(sentences)

  def nullfunc(self, match, node, depth, user):
    return xml.sax.saxutils.escape(ElementTree.tostring(node).decode('utf-8'))

  def do_br(self, match, node, depth, user):
    return '\n'

  def do_star(self, match, node, depth, user):
    pat = match[:match.index(self.magic_words['that'])]
    stars=[ m for m in pat if type(m) == list]
    ret = ' '.join(stars[int(node.get('index', 0))])
    #print("Returning star:", ret)
    return ret

  def do_that(self, match, node, depth, user):
    ind = [ int(x) for x in node.get('index', '1,1').split(',') ]
    ind.extend([1,1])
    try:
      return self.resp[-ind[0]][1][ind[1]]
    except IndexError:
      return ''

  def do_input(self, match, node, depth, user):
    ind = [ int(x) for x in node.get('index', '1,1').split(',') ]
    ind.extend([1,1])
    try:
      return self.resp[-ind[0]][0][ind[1]]
    except IndexError:
      return ''

  def do_thatstar(self, match, node, depth, user):
    pat = match[match.index(self.magic_words['that']):match.index(self.magic_words['topic'])]
    stars=[ m for m in pat if type(m) == list]
    return ' '.join(stars[int(node.get('index', 0))])

  def do_topicstar(self, match, node, depth, user):
    pat = match[match.index(self.magic_words['topic']):]
    stars=[ m for m in pat if type(m) == list]
    return ' '.join(stars[int(node.get('index', 0))])

  def do_get(self, match, node, depth, user):
    return self.user[user].get(node.get('name',''),'')

  def do_bot(self, match, node, depth, user):
    n=node.get('name','')
    return self.bot.get(n,n)

  def do_sr(self, match, node, depth, user):
    txt=self.do_star(match, node, depth)
    return self.match(txt, depth+1)

  def do_person2(self, match, node, depth, user):
    txt=''
    if len(node) == 0 and not node.text:
      txt=self.do_star(match, node, depth, user)
    else:
      txt=self.respond(match, node, user, depth)
    for k,v in AIMLParser.replacements['person2'].items():
      txt = txt.replace(k,v)
    return txt  # TODO: 2nd personify this

  def do_person(self, match, node, depth, user):
    txt=''
    if len(node)==0 and not node.text:
      txt=self.do_star(match, node, depth, user)
    else:
      txt=self.respond(match, node, user, depth)
    for k,v in AIMLParser.replacements['person'].items():
      txt = txt.replace(k,v)
    return txt  # TODO: personify this

  def do_gender(self, match, node, depth, user):
    txt=''
    if len(node)==0 and not node.text:
      txt=self.do_star(match, node, depth, user)
    else:
      txt=self.respond(match, node, user, depth)
    for k,v in AIMLParser.replacements['gender'].items():
      txt = txt.replace(k,v)
    return txt  # TODO: genderify this

  def do_date(self, match, node, depth, user):
    save_loc = locale.getlocale()
    if 'locale' in node.attrib:
      locale.setlocale(locale.LC_ALL, node.get('locale'))
    if 'timezone' in node.attrib:
      #LOG("Error: timezone attribute not implemented")
      pass
    s = datetime.date.today().strftime(node.get('format', '%c'))
    locale.setlocale(locale.LC_ALL, save_loc)

  def do_id(self, match, node, depth, user):
    return user

  def do_size(self, match, node, depth, user):
    return '0'

  def do_version(self, match, node, depth, user):
    return '1.0.1'

  def do_uppercase(self, match, node, depth, user):
    txt=self.respond(match, node, user, depth)
    return txt.upper()

  def do_lowercase(self, match, node, depth, user):
    txt=self.respond(match, node, user, depth)
    return txt.lower()

  def do_formal(self, match, node, depth, user):
    txt=self.respond(match, node, user, depth)
    return txt.title()

  def do_sentence(self, match, node, depth, user):
    txt=self.respond(match, node, user, depth)
    return txt.capitialize()

  def process_blockCond(self, match, node, depth, user):
    pred = self.makeInputPath(self.normalize(self.user[user].get(node['name'], '')))
    parser = AIMLParser()
    parser.addToGraph(parser.make_path(node['value']), '')
    if self._match(pred, parser.aiml_graph) == None:
      return ''
    return self.respond(match, node, depth, user)

  def process_singleCond(self, match, node, depth, user):
    choices = [n for n in list(node) if n.tag == 'li']
    pred = self.makeInputPath(self.normalize(self.user[user].get(node['name'], '')))
    for ch in choices:
      if 'value' in ch.keys():
        parser = AIMLParser()
        parser.addToGraph(parser.make_path(ch['value']), '')
        if self._match(pred, parser.aiml_graph) == None:
          continue
        del parser
      return self.respond(match, ch, depth, user) #default or succeed
    return ''

  def process_multiCond(self, match, node, depth, user):
    choices = [n for n in list(node) if n.tag == 'li']
    for ch in choices:
      if 'value' in ch.keys() and 'name' in ch.keys():
        pred = self.makeInputPath(self.normalize(self.user[user].get(ch['name'], '')))
        parser = AIMLParser()
        parser.addToGraph(parser.make_path(ch['value']), '')
        if self._match(pred, parser.aiml_graph) == None:
          continue
        del parser
      return self.respond(match, ch, depth, user) #default or succeed
    return ''

  def do_condition(self, match, node, depth, user):
    if 'name' in node.keys() and 'value' in node.keys():
      return self.process_blockCond(match, node, depth, user)
    elif 'name' in node.keys():
      return self.process_singleCond(match, node, depth, user)
    else:
      return self.process_multiCond(match, node, depth, user)
    
  def do_random(self, match, node, depth, user):
    choices = [n for n in list(node) if n.tag == 'li']
    #print(match, choices, user, depth)
    return self.respond(match, random.choice(choices), user, depth)

  def do_set(self, match, node, depth, user):
    name = node.get('name','')
    #print("Setting", name)
    txt = self.respond(match, node, user, depth)
    if not user in self.user:
      #LOG('WARNING: cannot find user session: ', user)
      pass
    self.user[user][name] = txt
    #print("Setting", name, '=', txt)
    return txt

  def do_gossip(self, match, node, depth, user):
    #LOG(self.respond(match, node, depth))
    return ''

  def do_srai(self, match, node, depth, user):
    #print("ENTERING SRAI")
    txt=self.respond(match, node, user, depth+1)
    return self.match(txt, depth+1)

  def do_think(self, match, node, depth, user):
    self.respond(match, node, user, depth)
    return ''

  def do_eval(self, match, node, depth, user):
    return self.respond(match, node, user, depth)

  def do_learn(self, match, node, depth, user):
    parser=AIMLParser()
    parser.aiml_graph=self.brain
    def replace_evals(n):
      while len(n) > 0 and n[0].tag == 'eval':
        n.text += self.do_eval(match, n[0], user, depth)
        n.remove(n[0])
      if len(n) > 0:
        last=n[0] #Can't be an <eval>
        for c in n:
          if c.tag == 'eval':
            last.tail += self.do_eval(match, c, user, depth)
            n.remove(c)
          else:
            replace_evals(c)
            last = c
    replace_evals(node)
    node.tag = 'aiml' # Treat the <learn> as an <aiml> for parsing
    parser._parse(node)
    self.brain = parser.aiml_graph

  def do_system(self, match, node, depth, user):
    return str(os.system(self.respond(match, node, user, depth)))

  def do_javascript(self, match, node, depth, user):
    #LOG('ERROR: Javascript not implemented')
    return ''

  def do_python(self, match, node, depth, user):
    # This allows python code to be parsed and executed
    txt=self.respond(match, node, user, depth)
    locs={'bot':self, 'ret':None}
    try:
      exec(txt, {}, locs)
    except Exception as e:
      #LOG('ERROR: exception handling python tag\n', e)
      pass
    return str(locs.get('ret', ''))

  def respond(self, match, template, user, depth=0):
    #print('*** Responding to:', match, '\n', template, '\n', user)
    #input('>')
    if depth > self.bot.get('recursion', 10):
      return ''
    txt = template.text if template.text else ''
    for n in list(template):
      txt+=getattr(self, "do_%s" % n.tag, self.nullfunc)(match, n, depth, user)
      if n.tail:
        txt += n.tail
    return txt

  def _match(self, path, node=None):
    if node == None: node = self.brain
    #print('Match start:', path, node.keys())
    if len(path) == 0:
      if self.magic_words['template'] in node:
        return [node[self.magic_words['template']]]
      else: return None
    # Match _ wildcard
    if '_' in node:
      n = node['_']
      for i in range(len(path)+1):
        #print('***Matching *', repr(path))
        if i>0 and path[:i][-1] in self.magic_words.values(): break
        m = self._match(path[i:], n)
        if m != None:
          m = [path[:i]] + m
          return m
    # Match real token
    if path[0] in node:
      #print('***Matching tok', repr(path))
      m = self._match(path[1:], node[path[0]])
      if m != None:
        m = [path[0]] + m
        return m
    # Match bot predicate
    if self.magic_words['bot'] in node:
      for name, d in node[self.magic_words['bot']].items():
        #TODO: replace name with bot predicate
        #print('***Matching bot', repr(path))
        if name.upper() == path[0]:
          m = self._match(path[1:], node[path[0]])
          if m != None:
            m = [path[0]] + m
            return m
    # Match * wildcard
    if '*' in node:
      n = node['*']
      for i in range(len(path)+1):
        #print('***Matching *', repr(path))
        if i>0 and path[:i][-1] in self.magic_words.values(): break
        m = self._match(path[i:], n)
        if m != None:
          m = [path[:i]] + m
          return m
    return None

  def normalize(self, inp):
    return inp.upper().translate(str.maketrans(string.punctuation + string.whitespace,'\x01'*len(string.punctuation) + ' '*len(string.whitespace))).split('\x01')

  def makeInputPath(self, inp):
    return [tok for tok in inp.split(' ') if tok != '']


def loadaiml(a, dir='alice/'):
  import glob
  for fn in glob.glob(os.path.join(dir, '*.aiml')):
    print('Parsing',fn)
    try:
      with codecs.open(fn, mode='r', encoding='UTF-8') as f:
        start = time.clock()
        a.parse(f)
        end = time.clock()
        print('Finished in', end - start, ' seconds')
    except UnicodeError as e:
      print('Failed to parse file due to unicode issues:', fn)

if __name__ == '__main__':
  import os.path, sys
  a = AIMLParser()
  brain = None
  t = time.clock()
  if len(sys.argv) > 1: #Get command-line filenames only
    for fn in sys.argv[1:]:
      print("Parsing", fn)
      with codecs.open(fn, mode='r', encoding='UTF-8') as f:
        a.parse(f)
    brain = Brain(a.aiml_graph)
    print('Total time:',time.clock() - t)
  elif not os.path.exists('brain.db'):  #Load all scripts
    loadaiml(a)
    brain = Brain(a.aiml_graph)
    print('Total time:',time.clock() - t)
    brain.saveBrain('brain.db')
  else:                 #Get saved brain
    brain = Brain()
    print('Loading brain...')
    brain.loadBrain('brain.db')
    print('Total time:',time.clock() - t)

  while 1:
    s = input('> ')
    print(brain.reply(s))

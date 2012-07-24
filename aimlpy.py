#!/usr/bin/env python
#from xml.dom import minidom
import xml.etree.ElementTree as ElementTree
import re
import string
import time
import shelve
import random
import datetime
import math
import collections

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
                    'mine': 'his'
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
                    }
              'person2': {
                    'I': 'you',  #1st -> 2nd person
                    'me': 'you',
                    'myself': 'yourself',
                    'mine': 'yours'
                    'my': 'your',

                    'we': 'you',
                    'us': 'you',
                    'ourselves': 'yourselves',
                    'ours': 'yours',
                    'our': 'your',
                    }
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
    return [ tok for tok in self.make_path.split_regex.split(pattern) if tok != None]

  def innerText(self, node):
    return ElementTree.tostring(node)[2+len(node.tag):-(4+len(node.tag))].strip().decode('utf-8', 'replace')

  def do_aiml(self, node):
    for n in list(node):
        self._parse(n)

  def do_topic(self, node):
    self._topic = node.get('name', '*')
    for n in list(node):
      self._parse(n)
    self._topic = '*'

  def do_category(self, node):
    template = ElementTree.tostring(node.find('template')).decode('utf-8', 'replace')
    pattern = node.find('pattern')
    pattern = self.make_path(self.innerText(pattern))
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

  def reply(self, msg, user):
    return self.match(msg, user, record=True)

  def match(self, inp, user, depth=0, record=False):
    current_node = self.brain
    matches = []
    for s in self.normalize(inp):
      s = self.makeInputPath(s) + [self.magic_words['that'],'', self.magic_words['topic'],'']
      match = self._match(s)
      if match == None: continue
      matches.append(match)
    sentences = []
    for m in matches:
      sentences.append(self.respond(m, ElementTree.fromstring(m[-1]), user, depth))
    if record:
      self.resp.append((inp, sentences))
    return ' '.join(sentences)

  def nullfunc(self, match, node, depth):
    return ElementTree.tostring(node)

  def do_star(self, match, node, depth, user):
    pat = match[:match.index(self.magic_words['that'])]
    stars=[ m for m in pat if type(m) == list]
    return stars[node.get('index', 0)]

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
    return stars[node.get('index', 0)]

  def do_topicstar(self, match, node, depth, user):
    pat = match[match.index(self.magic_words['topic']):]
    stars=[ m for m in pat if type(m) == list]
    return stars[node.get('index', 0)]

  def do_get(self, match, node, depth, user):
    return self.user[user].get(node.get('name',''),'')

  def do_bot(self, match, node, depth, user):
    return self.bot.get(node.get('name',''),'')

  def do_sr(self, match, node, depth, user):
    txt=self.do_star(match, node, depth)
    return self.match(txt, depth+1)

  """def do_person2(self, match, node, depth, user):
    txt=''
    if len(node) == 0 and not node.text:
      txt=self.do_star(match, node, depth, user)
    else:
      txt=self.respond(match, node, user, depth)
    return txt"""

  #def do_person(self, match, node, depth, user):
  #def do_gender(self, match, node, depth, user):

  def do_date(self, match, node, depth, user):
    return datetime.date.today().strftime('%c')

  def do_id(self, match, node, depth, user):
    return self._user

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

  """def do_condition(self, match, node, depth, user):
    pred=None
    if 'name' in node.keys() and 'value' in node.keys():
      s = self.makeInputPath(self.normalize(''))  #TODO: predicate
      return self.respond(match, node, user, depth) if self._match(s) else ''
    else if 'name' in node.keys():
      pred=None #TODO: predicate
    lis = [ n for n in list(node) if n.tag == 'li' ]
    default = None
    for li in lis:
      if 'name' in li.keys():
        pred = None #TODO: predicate
      if 'value' in li.keys():
        if self._match(
      if not ('name' in li.keys() or 'value' in li.keys()):
        default = li
        break

    return '' if default"""

  def do_random(self, match, node, depth, user):
    choices = [n for n in list(node) if n.tag == 'li']
    return self.respond(match, random.choice(choices), user, depth)

  def do_set(self, match, node, depth, user):
    txt = self.respond(match, node, user, depth)
    name = node.get('name','')
    self.user[self._user][name] = txt
    return txt

  def do_gossip(self, match, node, depth, user):
    #LOG(self.respond(match, node, depth))
    return ''

  def do_srai(self, match, node, depth, user):
    txt=self.respond(match, node, user, depth)
    return self.match(txt, depth+1)

  def do_think(self, match, node, depth, user):
    self.respond(match, node, user, depth)
    return ''

  def do_learn(self, match, node, depth, user):
    parser=AIMLParser()
    parser.aiml_graph=self.brain
    with open(self.respond(match, node, user, depth), 'r') as f:
      parser.parse(f)
    self.brain = parser.aiml_graph

  def do_system(self, match, node, depth, user):
    return str(os.system(self.respond(match, node, user, depth)))

  def do_javascript(self, match, node, depth, user):
    #LOG('WARNING: Javascript not implemented')
    return ''

  @static_var('safe_dict', dict([ (k, getattr(math, k)) for k in dir(math)[4:] ]+[('abs', abs), ('random', random.random)]) )
  def do_python(self, match, node, depth, user):
    txt=self.respond(match, node, user, depth)
    return str(eval(txt, {'__builtins__':None}, self.do_python.safe_dict))

  def respond(self, match, template, user, depth=0):
    if depth > self.bot['recursion']:
      return ''
    txt = template.text if template.text else ''
    for n in list(template):
      txt += getattr(self, "do_%s" % n.tag, self.nullfunc)(match, n, depth, user)
      if n.tail:
        txt += n.tail
    return txt

  def _match(self, path, node=None):
    if node == None: node = self.brain
    if len(path) == 0:
      if self.magic_words['template'] in node:
        return [node[self.magic_words['template']]]
      else: return None
    # Match _ wildcard
    if '_' in node and not (path[0] in self.magic_words.values()):
      #print('***Matching _', repr(path))
      n = node['_']
      for i in range(len(path)):
        if path[i] in self.magic_words.values(): break
        m = self._match(path[i+1:], n)
        if m != None:
          m = [path[:i+1]] + m
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
      #print('***Matching bot', repr(path))
      for name, d in node[self.magic_words['bot']].items():
        #TODO: replace name with bot predicate
        if name.upper() == path[0]:
          m = self._match(path[1:], node[path[0]])
          if m != None:
            m = [path[0]] + m
            return m
    # Match * wildcard
    if '*' in node and not (path[0] in self.magic_words.values()):
      #print('***Matching *', repr(path))
      n = node['*']
      for i in range(len(path)):
        if path[i] in self.magic_words.values(): break
        m = self._match(path[i+1:], n)
        if m != None:
          m = [path[:i+1]] + m
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
      with open(fn, 'r') as f:
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
      with open(fn, 'r') as f:
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
    print(brain.match(s, record=True))
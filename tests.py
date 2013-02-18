#!/usr/bin/env python3
import unittest
import aimlpy
import datetime
import codecs
import functools
import pdb
import sys

DEBUG = True

def debug_on(*exceptions):
  global DEBUG
  if not exceptions:
    exceptions = (AssertionError, )
  if not DEBUG:
    return lambda fu: fu
  else:
    def decorator(f):
      @functools.wraps(f)
      def wrapper(*args, **kwargs):
        try:
          return f(*args, **kwargs)
        except exceptions:
          pdb.post_mortem(sys.exc_info()[2])
      return wrapper
    return decorator

def files(*args):
  def decorator(cls):
    cls.files = args
    return cls
  return decorator

def input(st):
  def decorator(cls):
    cls.inputString = st
    return cls
  return decorator

class PyAIMLTest:
  @classmethod
  def setUpClass(cls):
    a = aimlpy.AIMLParser()
    for fn in getattr(cls, 'files', []):
      with codecs.open(fn, mode='r', encoding='UTF-8') as f:
        a.parse(f)
    s = getattr(cls, 'inputString', None)
    if s:
      a.parseString(s)
    cls.bot = aimlpy.Brain(a.aiml_graph)
  def setUp(self):
    self.bot = self.__class__.bot

# -- Actual tests --

@files('alice/self-test.aiml')
class SimpleResponseTests(PyAIMLTest, unittest.TestCase):
  @debug_on()
  def test_bot(self):
    self.assertEqual(self.bot.reply('TEST BOT'), 'My name is')
    self.bot.bot['name'] = 'Jordi'
    self.assertEqual(self.bot.reply('TEST BOT'), 'My name is Jordi')

  def test_condition(self):
    self.bot.user['Alice'] = { 'gender': 'female' }
    self.bot.user['Bob'] = { 'gender': 'male' }
    self.assertEqual(self.bot.reply('TEST CONDITION NAME VALUE'), '')
    self.assertEqual(self.bot.reply('TEST CONDITION NAME VALUE', 'Alice'), '')
    self.assertEqual(self.bot.reply('TEST CONDITION NAME VALUE', 'Bob'), 'You are handsome')

    self.assertEqual(self.bot.reply('TEST CONDITION NAME'), 'You are genderless')
    self.assertEqual(self.bot.reply('TEST CONDITION NAME', 'Alice'), 'You are beautiful')
    self.assertEqual(self.bot.reply('TEST CONDITION NAME', 'Bob'), 'You are handsome')

    self.assertEqual(self.bot.reply('TEST CONDITION'), 'You are genderless')
    self.assertEqual(self.bot.reply('TEST CONDITION', 'Alice'), 'You are beautiful')
    self.assertEqual(self.bot.reply('TEST CONDITION', 'Bob'), 'You are handsome')

  def test_date(self):
    ## TODO: add testing of formatting
    d = self.bot.reply('TEST DATE')[len('The date is '):]
    try:
      datetime.datetime.strptime(d, '%c')
    except ValueError:
      self.fail('Failed to parse date: d')

  def test_formal(self):
    self.assertEqual(self.bot.reply('TEST FORMAL'), 'Formal Test Passed')

  def test_gender(self):
    """She'd told him she heard that his hernia is history --v"""
    self.assertEqual(self.bot.reply('TEST GENDER'), "he'd told her he heard that her hernia is history")

  def test_getset(self):
    self.assertEqual(self.bot.reply('TEST GET AND SET'), 'cheese. My favorite food is cheese')

  def test_gossip(self):
    pass

  def test_id(self):
    self.assertEqual(self.bot.reply('TEST ID'), 'Your id is')
    self.assertEqual(self.bot.reply('TEST ID', 'Alice'), 'Your id is Alice')

  def test_input(self):
    ## TODO: More tests on bounds, empty, etc.
    self.bot.reply('TEST')
    self.assertEqual(self.bot.reply('TEST INPUT'), 'You just said: TEST')

  @unittest.skip("Not yet implemented")
  def test_javascript(self):
    pass 

  def test_lowercase(self):
    self.assertEqual(self.bot.reply('TEST LOWERCASE'), 'The Last Word Should Be lowercase') 

  def test_person(self):
    ## TODO: add more cases.
    self.assertEqual(self.bot.reply('TEST PERSON'), 'He is a cool guy.')

  def test_person2(self):
    ## TODO: add more cases.
    self.assertEqual(self.bot.reply('TEST PERSON2'), 'You are a cool guy.')

  def test_random(self):
    self.assertEqual(self.bot.reply('TEST RANDOM EMPTY'), 'Nothing here!') 
    picks=[]
    for i in range(100): #Try 100x's to get all possible choices
      if len(picks) == 3: break
      d=self.bot.reply('TEST RANDOM')[-1]
      if not d in picks: picks.append(d)
    else:
      self.fail('Unable to get all possiblities after 100 tries...')

  def test_sentence(self):
    self.assertEqual(self.bot.reply('TEST SENTENCE'), 'My first letter should be capitalized.') 
    
  def test_size(self):
    d=self.bot.reply('TEST SIZE')[len("I've learned "):-len(' categories')]
    try:
      int(d)
    except ValueError:
      self.fail('Failed to parse number of categories')

  def test_sr(self):
    self.assertEqual(self.bot.reply('TEST SRAI'), 'srai test passed')
    self.assertEqual(self.bot.reply('TEST SR SRAI TARGET'), 'srai results: srai test passed')
    self.assertEqual(self.bot.reply('TEST NESTED SR SRAI TARGET'), 'srai results: srai test passed')
    self.assertEqual(self.bot.reply('TEST SRAI INFINITE'), '')

  def test_star(self):
    self.assertEqual(self.bot.reply('BLAH1 TEST STAR BEGIN'), 'Begin star matched: BLAH1')
    self.assertEqual(self.bot.reply('TEST STAR BLAH2 MIDDLE'), 'Middle star matched: BLAH2')
    self.assertEqual(self.bot.reply('TEST STAR END BLAH3'), 'End star matched: BLAH3')
    self.assertEqual(self.bot.reply('TEST STAR STAR1 MULTIPLE STAR2 MAKES ME STAR3'), 'Multiple stars matched: STAR1, STAR2, STAR3')

  def test_system(self):
    self.assertEqual(self.bot.reply('TEST SYSTEM'), 'The system says hello!')
    
  def test_that(self):
    self.assertEqual(self.bot.reply('SRAI TARGET'), 'srai test passed')
    self.assertEqual(self.bot.reply('TEST THAT'), 'I just said: srai test passed')
    self.assertEqual(self.bot.reply('TEST THAT'), 'I have already answered this question')

  def test_thatstar(self):
    self.assertEqual(self.bot.reply('TEST THATSTAR'), 'I say beans')
    self.assertEqual(self.bot.reply('TEST THATSTAR'), 'I just said "BEANS"')
    self.assertEqual(self.bot.reply('TEST THATSTAR MULTIPLE'), 'I say beans and franks for everybody')
    self.assertEqual(self.bot.reply('TEST THATSTAR MULTIPLE'), 'Yes, BEANS and FRANKS for all!')

  def test_think(self):
    self.assertEqual(self.bot.reply('TEST THINK'), '')

  def test_topic(self):
    self.assertEqual(self.bot.reply('TEST TOPIC'), 'What are we talking about?')
    self.bot.user['']['__TOPIC__'] = 'FRUIT'
    self.assertEqual(self.bot.reply('TEST TOPIC'), 'We were discussing apples and oranges')

  def test_topicstar(self):
    self.assertEqual(self.bot.reply('TEST TOPICSTAR'), 'I have no topic')
    self.bot.user['']['__TOPIC__'] = 'Soylent Green'
    self.assertEqual(self.bot.reply('TEST TOPICSTAR'), 'Soylent Green is made of people')
    self.bot.user['']['__TOPIC__'] = 'Soylent Green and Blue'
    self.assertEqual(self.bot.reply('TEST TOPICSTAR'), 'Both Soylents Green and Blue are made of people')

  def test_uppercase(self):
    self.assertEqual(self.bot.reply('TEST UPPERCASE'), 'The Last Word Should Be UPPERCASE')

  def test_version(self):
    self.assertEqual(self.bot.reply('TEST VERSION'), 'PyAIML is version 1.0.1')

  @unittest.expectedFailure
  def test_unicode(self):
    self.assertEqual(self.bot.reply('ÔÇÉÏºÃ'), 'Hey, you speak Chinese! ÔÇÉÏºÃ')

  @unittest.expectedFailure
  def test_whitespace(self):
    self.assertEqual(self.bot.reply('TEST WHITESPACE'), 'Extra   Spaces\n   Rule!   (but not in here!)  But   Here  They  Do!')

  def test_python(self):
    self.assertEqual(self.bot.reply('TEST PYTHON'), 'Hello World!')

  def test_learn(self):
    ## TODO: Test eval tags
    self.assertEqual(self.bot.reply('LEARN TARGET SUCCESS'), 'What?')
    self.assertEqual(self.bot.reply('TEST LEARN'), 'DONE')
    self.assertEqual(self.bot.reply('LEARN TARGET SUCCESS'), 'Ahhhhh...')

if __name__ == '__main__':
  unittest.main()

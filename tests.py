#!/usr/env python3
import unittest
import aimlpy

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
      with open(fn, 'r') as f:
        a.parse(f)
    s = getattr(cls, 'inputString', None)
    if s:
      a.parseString(s)
    cls.bot = aimlpy.Brain(a.aiml_graph)
  def setUp(self):
    self.bot = self.__class__.bot

# -- Actual tests --

@files('alice/update1.aiml')
class SimpleResponseTests(PyAIMLTest, unittest.TestCase):
  def test_atomic(self):
    self.assertEqual(self.bot.reply('I AM ON MY WAY'), 'See you soon.')
    self.assertEqual(self.bot.reply('I aM On My wAY'), 'See you soon.')

  def test_wildcard(self):
    self.assertEqual(self.bot.reply('THINKING OUTSIDE THE BOX'), 'You have an open mind.')
    self.assertEqual(self.bot.reply('THINKING OUTSIDE THE CAR'), 'You have an open mind.')
    self.assertEqual(self.bot.reply('THINKING OUTSIDE THE BIG BLACK BOX'), 'You have an open mind.')
    self.assertEqual(self.bot.reply('snow is not white'), 'grass is green')
    self.assertEqual(self.bot.reply('snow is not blue'), 'snow is white.')

  def test_star(self):
    self.assertEqual(self.bot.reply('SET THEY 1 2 3', 'user1'), '')
    self.assertEqual(self.bot.user['user1']['they'], '1 2 3')

  def test_that(self):
    pass

  def test_bot(self):
    self.assertEqual(self.bot.reply('enterprise come in'), 'name here.')
    self.bot.bot['name'] = 'Jordi'
    self.assertEqual(self.bot.reply('enterprise come in'), 'Jordi here.')
    self.bot.reply('FORMAT PROPERTIES')

  def test_srai(self):
    self.assertEqual(self.bot.reply('consider it quiet'), 'Then we can hear each other better.')

  def test_random(self):
    self.bot.reply('test link')
    self.bot.reply('test link')

if __name__ == '__main__':
  unittest.main()

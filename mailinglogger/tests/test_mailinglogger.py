import logging

from mailinglogger.MailingLogger import MailingLogger
from mailinglogger.tests.shared import DummySMTP, _setUp, _tearDown
from unittest import TestCase


class TestMailingLogger(TestCase):

    def getLogger(self):
        return logging.getLogger('')

    def setUp(self):
        _setUp(None, self, stdout=False)

    def tearDown(self):
        _tearDown(None, self)

    def test_imports(self):
        from mailinglogger.MailingLogger import MailingLogger
        from mailinglogger import MailingLogger

    def test_default_flood_limit(self):
        # set up logger
        self.handler = MailingLogger('from@example.com', ('to@example.com',))
        logger = self.getLogger()
        logger.addHandler(self.handler)
        # log 11 entries
        for i in range(12):
            logger.critical('message')
        # only 1st 10 should get sent
        # +1 for the final warning
        self.assertEqual(len(DummySMTP.sent), 11)

    def test_flood_protection_bug(self):
        # set up logger
        self.handler = MailingLogger('from@example.com', ('to@example.com',),
                                     flood_level=1)
        logger = self.getLogger()
        logger.addHandler(self.handler)
        # make it 11pm
        self.datetime.set(2007, 3, 15, 23)
        # paranoid check
        self.assertEqual(len(DummySMTP.sent), 0)
        # log until flood protection kicked in
        logger.critical('message1')
        logger.critical('message2')
        # check - 1 logged, 1 final warning
        self.assertEqual(len(DummySMTP.sent), 2)
        # check nothing emitted
        logger.critical('message3')
        self.assertEqual(len(DummySMTP.sent), 2)
        # advance time past midnight
        self.datetime.set(2007, 3, 15)
        # log again
        logger.critical('message4')
        # check we are emitted now!
        self.assertEqual(len(DummySMTP.sent), 3)

    def test_headers_supplied_get_added_to_those_generated(self):
        # set up logger
        self.handler = MailingLogger('from@example.com', ('to@example.com',),
                                     headers={'From': 'someidiot',
                                              'to': 'someidiot'})
        logger = self.getLogger()
        logger.addHandler(self.handler)
        logger.critical('message')
        self.assertEqual(len(DummySMTP.sent), 1)
        m = DummySMTP.sent[0][3]
        # the headers specified in the `headers` parameter get added
        # to those generated by mailinglogger - be careful!
        self.assertTrue('From: from@example.com' in m)
        self.assertTrue('From: someidiot' in m)
        # however, if you try hard you *can* break things :-S
        self.assertTrue('To: to@example.com' in m)
        self.assertTrue('to: someidiot' in m)

    def test_subject_contains_date(self):
        # set up logger
        self.handler = MailingLogger('from@example.com', ('to@example.com',),
                                     subject="%(asctime)s")
        logger = self.getLogger()
        logger.addHandler(self.handler)
        logger.critical('message')
        self.assertEqual(len(DummySMTP.sent), 1)
        m = DummySMTP.sent[0][3]
        self.assertTrue('Subject: 2007-01-01 10:00:00,000' in m, m)

    def test_non_string_error_messages_dont_break_logging(self):
        self.handler = MailingLogger('from@example.com', ('to@example.com',),)
        logger = self.getLogger()
        logger.addHandler(self.handler)
        logger.critical(object())
        self.assertEqual(len(DummySMTP.sent), 1)

    def test_template(self):
        self.handler = MailingLogger('from@example.com', ('to@example.com',),
                                     template="<before>%s<after>")
        logger = self.getLogger()
        logger.addHandler(self.handler)
        logger.critical('message')
        m = DummySMTP.sent[0][3]
        self.assertTrue('Subject: message' in m, m)
        self.assertTrue('<before>message<after>' in m, m)

    def test_default_charset(self):
        self.handler = MailingLogger('from@example.com', ('to@example.com',), )
        logger = self.getLogger()
        logger.addHandler(self.handler)
        logger.critical(u"accentu\u00E9")
        m = DummySMTP.sent[0][3]
        # lovely, utf-8 encoded goodness
        self.assertTrue('Subject: =?utf-8?b?YWNjZW50dcOp?=' in m, m)
        self.assertTrue('Content-Type: text/plain; charset="utf-8"' in m, m)
        self.assertTrue('\nYWNjZW50dcOp' in m, m)

    def test_specified_charset(self):
        self.handler = MailingLogger('from@example.com', ('to@example.com',),
                                     charset='iso-8859-1')
        logger = self.getLogger()
        logger.addHandler(self.handler)
        logger.critical(u"accentu\u00E9")
        m = DummySMTP.sent[0][3]
        # lovely, latin-1 encoded goodness
        self.assertTrue('\naccentu=E9' in m, m)
        self.assertTrue(
            'Content-Type: text/plain; charset="iso-8859-1"' in m, m)
        # no idea why MIMEText doesn't use iso-8859-1 here, best not to
        # argue...
        self.assertTrue('Subject: =?utf-8?b?YWNjZW50dcOp?=' in m, m)

    def test_specified_content_type(self):
        self.handler = MailingLogger('from@example.com', ('to@example.com',),
                                     content_type='foo/bar')
        logger = self.getLogger()
        logger.addHandler(self.handler)
        logger.critical(u"message")
        m = DummySMTP.sent[0][3]
        # NB: we drop the 'foo'
        self.assertTrue('Content-Type: text/bar' in m, m)

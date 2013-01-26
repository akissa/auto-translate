#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4
# Baruwa - Web 2.0 MailScanner front-end.
# Copyright (C) 2010-2012  Andrew Colin Kissa <andrew@topdog.za.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Automatic translation using m$ translator
    :copyright: 2012 Andrew Colin Kissa
    :copyright: © 2011 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""

import os
import re
import json
import time
import urllib
import logging
import datetime

import requests

from optparse import OptionParser

from polib import pofile



__all__ = ['Translator', 'TranslateApiException']


class ArgumentException(Exception):
    """Argument"""
    def __init__(self, message):
        self.message = message.replace('ArgumentException: ', '')
        super(ArgumentException, self).__init__(self.message)


class ArgumentOutOfRangeException(Exception):
    """ArgumentOutOfRange"""
    def __init__(self, message):
        self.message = message.replace('ArgumentOutOfRangeException: ', '')
        super(ArgumentOutOfRangeException, self).__init__(self.message)


class TranslateApiException(Exception):
    """TranslateApi"""
    def __init__(self, message, *args):
        self.message = message.replace('TranslateApiException: ', '')
        super(TranslateApiException, self).__init__(self.message, *args)


class Translator(object):
    """Implements AJAX API for the Microsoft Translator service
    
    """
    lang_url = 'http://api.microsofttranslator.com/V2/Ajax.svc/GetLanguagesForTranslate'
    oauth_url = 'https://datamarket.accesscontrol.windows.net/v2/OAuth2-13'
    translate_url = "http://api.microsofttranslator.com/V2/Ajax.svc/Translate"
    translate_array_url = "http://api.microsofttranslator.com/V2/Ajax.svc/TranslateArray"

    def __init__(self, client_id, client_secret,
            scope="http://api.microsofttranslator.com", debug=False):
        """


        :param client_id: The client ID that you specified when you registered
                          your application with Azure DataMarket.
        :param client_secret: The client secret value that you obtained when
                              you registered your application with Azure
                              DataMarket.
        :param scope: Defaults to http://api.microsofttranslator.com
        :param debug: If true, the logging level will be set to debug
        """

        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.grant_type = "client_credentials"
        self.access_token = None
        self.debug = debug
        self.logger = logging.getLogger("microsofttranslator")
        self.session = None
        self.langs = []
        if self.debug:
            self.logger.setLevel(level=logging.DEBUG)

    def create_session(self):
        "create a requests session"
        self.session = requests.session()

    def get_access_token(self, force=None):
        """
        .. note::
            The value of access token can be used for subsequent calls to the
            Microsoft Translator API. The access token expires after 10
            minutes. It is always better to check elapsed time between time at
            which token issued and current time. If elapsed time exceeds 10
            minute time period renew access token by following obtaining
            access token procedure.

        :return: The access token to be used with subsequent requests
        """
        args = urllib.urlencode({
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scope,
            'grant_type': self.grant_type
        })

        if not self.session or force:
            self.create_session()

        response = json.loads(self.session.post(
            self.oauth_url,
            data=args
        ).content)
        self.access_token = response['access_token']
        return self.access_token
        

    def call(self, url, params):
        """Calls the given url with the params urlencoded
        """
        if not self.access_token:
            self.get_access_token()

        if not self.session:
            self.create_session()

        headers = {'Authorization': 'Bearer %s' % self.access_token}
        translation_url = '%s?%s' % (url, urllib.urlencode(params))
        response = self.session.get(translation_url, headers=headers)
        retval = json.loads(response.content.decode("UTF-8-sig"))

        if isinstance(retval, basestring) and \
                retval.startswith("ArgumentOutOfRangeException"):
            raise ArgumentOutOfRangeException(retval)

        if isinstance(retval, basestring) and \
                retval.startswith("TranslateApiException"):
            raise TranslateApiException(retval)

        if isinstance(retval, basestring) and \
                retval.startswith("ArgumentException"):
            self.access_token = None
            raise ArgumentException(retval)

        return retval

    def languages(self):
        """Check languages supported"""
        if not self.session:
            self.create_session()

        if not self.langs:
            self.langs = self.call(self.lang_url, {})
        return self.langs

    def translate(self, text, to_lang, from_lang=None,
            content_type='text/plain'):
        """Translates a text string from one language to another.

        :param text: A string representing the text to translate.
        :param to_lang: A string representing the language code to
            translate the text into.
        :param from_lang: A string representing the language code of the
            translation text. If left None the response will include the
            result of language auto-detection. (Default: None)
        :param content_type: The format of the text being translated.
            The supported formats are "text/plain" and "text/html". Any HTML
            needs to be well-formed.
        """
        params = {
            'text': text.encode('utf8'),
            'to': to_lang,
            'contentType': content_type,
            'category': 'general',
            }
        if from_lang is not None:
            params['from'] = from_lang
        return self.call(self.translate_url, params)

    def translate_array(self, texts, to_lang, from_lang=None, **options):
        """Translates an array of text strings from one language to another.

        :param texts: A list containing texts for translation.
        :param to_lang: A string representing the language code to 
            translate the text into.
        :param from_lang: A string representing the language code of the 
            translation text. If left None the response will include the 
            result of language auto-detection. (Default: None)
        :param options: A TranslateOptions element containing the values below. 
            They are all optional and default to the most common settings.

                Category: A string containing the category (domain) of the 
                    translation. Defaults to "general".
                ContentType: The format of the text being translated. The 
                    supported formats are "text/plain" and "text/html". Any 
                    HTML needs to be well-formed.
                Uri: A string containing the content location of this 
                    translation.
                User: A string used to track the originator of the submission.
                State: User state to help correlate request and response. The 
                    same contents will be returned in the response.
        """
        options = {
            'Category': "general",
            'Contenttype': "text/plain",
            'Uri': '',
            'User': 'default',
            'State': ''
            }.update(options)
        params = {
            'texts': json.dumps(texts),
            'to': to_lang,
            'options': json.dumps(options),
            }
        if from_lang is not None:
            params['from'] = from_lang

        return self.call(self.translate_array_url, params)


def format_date():
    "Return a date string in required format"
    return time.strftime("%Y-%m-%d %R+0200", time.strptime(time.ctime()))


def first_pass(items, thestring):
    "replace %(xxx)s vars"
    for item in items:
        thestring = thestring.replace(item, '|^^|', 1)
    return thestring


def second_pass(items, thestring):
    "replace %s with actual %(xxx)s"
    for item in items:
        thestring = thestring\
                    .replace('|^^|', item, 1)\
                    .replace('| ^ ^ |', item, 1)
    return thestring


def getpofs(matched, dirname, files):
    "utility to get po files"
    matched.extend([os.path.join(dirname, filename)
                    for filename in files
                    if filename.endswith('.po')])

def get_lang(dirname):
    "Get the language from directory name"
    return os.path.basename(
                os.path.dirname(
                    os.path.dirname(dirname)
                )
            )

def process(translator, raw_entry, language, sentry, regex):
    "Process and Translate the string"
    languages_bidi = ["he", "ar", "fa", "yi"]
    found = regex.findall(raw_entry)
    if found:
        if language in languages_bidi:
            return None
        raw_entry = first_pass(found, raw_entry)
    if datetime.datetime.now() >= sentry:
        print "Renewing token"
        translator.get_access_token(True)
        sentry = (datetime.datetime.now() +
                datetime.timedelta(minutes=8))
    new_entry = translator.translate(raw_entry, language)
    if found:
        new_entry = second_pass(found, new_entry)
    return new_entry
        

def createps(filename, client_id, api_key, meta, default_lang):
    "update po file"
    do_save = False
    trans = Translator(client_id, api_key)
    print "Processing: %s" % filename
    pobj = pofile(filename)
    lang = get_lang(filename)
    

    if (not lang in trans.languages() or lang == default_lang) and lang != 'zh':
        print "Language: %s not supported by API" % lang
        return

    try:
        match_re = re.compile(r'((?:%\([^\W]{1,}\)(?:s|d))|(?:{{\w+}}))')
        sentry = datetime.datetime.now() + datetime.timedelta(minutes=8)
        if lang == 'zh':
            lang = 'zh-CHS'
        for entry in pobj.untranslated_entries():
            try:
                msgstr = process(trans, entry.msgid, lang, sentry, match_re)
                if entry.msgid_plural:
                    if msgstr:
                        entry.msgstr_plural['0'] = msgstr
                    msgstr_plural = process(trans, entry.msgid_plural,
                                            lang, sentry, match_re)
                    if msgstr_plural:
                        entry.msgstr_plural['1'] = msgstr_plural
                else:
                    if msgstr:
                        entry.msgstr = msgstr
                do_save = True
            except (TranslateApiException, ArgumentOutOfRangeException), ermsg:
                print 'Error occured: %s' % str(ermsg)

        if do_save:
            pobj.metadata.update(meta)
            pobj.metadata['PO-Revision-Date'] = format_date()
            pobj.save(filename)
    except ArgumentException, errstr:
        print "Access Error: %s" % str(errstr)


if __name__ == '__main__':
    # Run tings mon

    CLIENT_ID = 'xxxxxxx'
    API_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

    metadata = {
        'Report-Msgid-Bugs-To': 'baruwa@lists.baruwa.org',
        'Last-Translator': 'Andrew Colin Kissa <andrew@topdog.za.net>',
        'Generated-By': 'auto-translate.py 0.0.1',
        'Language-Team': 'Baruwa Project',
    }

    usage = "usage: %prog directory"
    parser = OptionParser(usage)
    parser.add_option('-s', '--source', dest="source_lang", default="en")
    opts, arguments = parser.parse_args()

    if len(arguments) != 1:
        parser.error("Please specify the directory to process")

    directory = arguments[0]

    if not os.path.exists(directory):
        parser.error("Directory: %s does not exist" % directory)

    try:        
        pofiles = []
        os.path.walk(directory, getpofs, pofiles)
        _ = [createps(path, CLIENT_ID, API_KEY, metadata, opts.source_lang)
            for path in pofiles]
    except KeyboardInterrupt:
        print "\nCTRL-C pressed, exiting"

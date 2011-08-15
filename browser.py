#!/usr/bin/env python
#
# vim:ts=4:sw=4:expandtab
######################################################################

"""Worker task: does the actual browsing work."""

import gtk
import sys
import pywebkitgtk as webkit
import random
from datetime import datetime
from datetime import timedelta
import time
import os
import getopt
import argparse
import uuid
import logging
from collections import deque
from logging import *
import gobject
import signal

class TimeoutException(Exception): 
    pass 

def randstr(l = 32):
    return "".join(["%.2x" % random.randint(0, 0xFF) for i in range(l/2)])

class DOMWalker:
    def __init__(self, branch_factor):
        self.__indent = 0
        self.branch_factor = branch_factor
        self.child_urls = []

    def __dump(self, node):
        i = 0
        #print >> sys.stderr,  " "*self.__indent, node.__class__.__name__
        if node.nodeName == "A" and self.branch_factor > 0:
            #print >> sys.stderr,  " "*self.__indent, node.__class__.__name__
            if node.hasAttribute("href") and  node.__getattribute__("href").find("http") != -1:
                #print >> sys.stderr,  "  "*self.__indent, node.__getattribute__("href")
                urlval = node.__getattribute__("href")
                self.child_urls.append(urlval)
                #print >> sys.stderr,  "  "*self.__indent, "http://safly-beta.dyndns.org/?q="+node.__getattribute__("href")
                #print >> sys.stderr,  "  "*self.__indent, node.nodeName
                self.branch_factor -= 1

    def walk_node(self, node, callback = None, *args, **kwargs):
        if callback is None:
            callback = self.__dump

        callback(node, *args, **kwargs)
        self.__indent += 1
        children = node.childNodes
        for i in range(children.length):
            child = children.item(i)
            self.walk_node(child, callback, *args, **kwargs)
            self.__indent -= 1


class Browser():
    def __init__(self, branch_factor=0):
        self.branch_factor = branch_factor
        self.__bid = randstr(16)
        self.__webkit = webkit.WebView()
        self.__webkit.SetDocumentLoadedCallback(self._DOM_ready)
        self.result = None
        self.tid = None
        self.timed_out = None
        info("Spawned new browser " + str(self.__bid))

    def __del__(self):
        pass

    def __timeout_callback(self):
        debug("Timeout Callback")
        if gtk.main_level() > 0:
            gtk.mainquit()
        # Set a flag so that the main thread knows to raise a
        # TimeoutException.
        self.timed_out = True
        # CAUTION: don't raise a TimeoutException here as we are in GTK
        # thread context. An exception raised here will not be seen by
        # the primary thread.
        # Don't do this: raise TimeoutException

    #if loading a page taked more than timeout miliseconds
    #visit will timout. Default timeout value is 5000
    def visit(self, url, timeout=5):
        info("Visiting URL: " + url)
        timeout_ms = timeout*1000
        self.timed_out = False
        self.tid = gobject.timeout_add(timeout_ms, self.__timeout_callback)
        self.pageLoaded = False
        self.walker = DOMWalker(self.branch_factor)
        self.__webkit.LoadDocument(url)
        gtk.main()
        # Disable the timeout since it is now clear that the page
        # loaded.
        if self.tid:
            gobject.source_remove(self.tid)
            self.tid = None
        if self.timed_out:
            raise TimeoutException
        else:
            return self.result[0], self.result[1], self.result[2], self.walker.child_urls

    def url(self):
        window = self.__webkit.GetDomWindow()
        return window.location.href

    def _DOM_node_inserted(self, event):
        target = event.target
        # target can be: Element, Attr, Text, Comment, CDATASection,
        # DocumentType, EntityReference, ProcessingInstruction
        parent = event.relatedNode
        #print >> sys.stderr,  "NODE INSERTED", target, parent

    def _DOM_node_removed(self, event):
        target = event.target
        # target can be: Element, Attr, Text, Comment, CDATASection,
        # DocumentType, EntityReference, ProcessingInstruction
        parent = event.relatedNode
        #print >> sys.stderr,  "NODE REMOVED", target, parent

    def _DOM_node_attr_modified(self, event):
        target = event.target
        # target can be: Element
        name = event.attrName
        change = event.attrChange
        newval = event.newValue
        oldval = event.prevValue
        parent = event.relatedNode
        #print >> sys.stderr,  "NODE ATTR MODIFIED", target, name, change, newval, oldval, parent

    def _DOM_node_data_modified(self, event):
        target = event.target
        # target can be: Text, Comment, CDATASection, ProcessingInstruction
        parent = event.target.parentElement
        newval = event.newValue
        oldval = event.prevValue
        #print >> sys.stderr,  "NODE DATA MODIFIED", target, newval, oldval, parent
        #print >> sys.stderr,  dir(target)
        #print >> event.target.getElementsByTagName('div').nodeName
        #print >> event.target.attributes[0].nodeName
        node=event.target.parentElement
        #print target.textContent
        #print target.parentElement.attributes.length

        if node.attributes:
            for i in range(node.attributes.length):
                attribute = node.attributes.item(i)
                attrName = attribute.nodeName
                attrValue = attribute.nodeValue
                #print attrName, "-->", attrValue
                if attrName == "name" and attrValue == "is_loaded":
                    #print node.innerHTML;
                    #print target.textContent
                    if node.innerHTML == "1":
                        self._is_Page_Loaded()

        #print dir(event.target)

    def _DOM_ready(self):
        document = self.__webkit.GetDomDocument()
        window = self.__webkit.GetDomWindow()
        document.addEventListener('DOMNodeInserted', self._DOM_node_inserted,
                                        False)
        document.addEventListener('DOMNodeRemoved', self._DOM_node_removed,
                                        False)
        document.addEventListener('DOMAttrModified', self._DOM_node_attr_modified,
                                        False)
        document.addEventListener('DOMCharacterDataModified', self._DOM_node_data_modified,
                                        False)
        #print >> sys.stderr,  "URL:", document.URL
        #print >> sys.stderr,  "Title:", document.title
        #print >> sys.stderr,  "Cookies:", document.cookie
        #print body, dir(body)
        #print "INNER:", document.innerHTML
        #print "OUTER:", body.outerHTML
        #print dir(document)
        #print str(document)
        # Save results so that we can return it on visit() calls.
        self.result = document.title, document.cookie, document.body.outerHTML
        self.walker.walk_node(document)
        # _DOM_ready may be called before we call gtk.main() -- see
        # visit() -- in which case calling mainquit is invalid. We check
        # for that here.
        if gtk.main_level() > 0:
            gtk.mainquit()

    def _is_Page_Loaded(self):
        debug("_is_Page_Loaded")
        self.pageLoaded = True
        gtk.mainquit()

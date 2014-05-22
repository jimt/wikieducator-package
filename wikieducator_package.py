#!/usr/bin/python -u
#
# WikiEducator Collection package hack
#
# Copyright (c) 2008-2011 James Tittsler
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# 20080118 jwt@OnJapan.net
"""a quick hack to package WikiEducator collections"""

import cgi
import cgitb; cgitb.enable()
import os
import sys
import uuid
import codecs
import re
import glob
import shutil
from urllib import unquote
import urllib2
import zipfile
from tempfile import mkdtemp
from BeautifulSoup import BeautifulSoup, Tag

IMSCP, SCORM12, IMSCC = range(3)
from wikieducator_package_config import *

def uuid4():
    return uuid.uuid4().hex
def uuid1():
    return uuid.uuid1().hex

def show_form(title = 'WikiEducator Package Export', message = ''):
    print '''<html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <title>%s</title>
  <style type="text/css">
body {
  font: 13.34px helvetica,arial,freesans,clean,sans-serif;
  line-height: 1.4;
}

p.error {
  color: red;
}
p.version {
  color: gray;
  font-size: smaller;
}
table {
  padding: 10px;
  border: solid #000 1px;
}
td.stepno {
  text-align: center;
  font-weight: bold;
  vertical-align: top;
}
td {
  text-align: left;
  vertical-align: top;
}

  </style>
</head>
<body>
<h1>%s</h1>
<form action="%s" method="post">
<ol>
  <li>Collaboratively author your content on <a href="http://wikieducator.org/">WikiEducator</a>.</li>
  <li>Gather the pages together in a <a href="http://wikieducator.org/Help:Books">book</a>.</li>
  <li>Enter the URL to the book:<br />
''' % (cgi.escape(title), cgi.escape(title), form_action)
    if message:
        print '''<p class="error">%s</font></p>\n''' % cgi.escape(message)
    print '''<input type="text" size=80 name="url" /><br />
    <i>e.g.</i> http://wikieducator.org/User:JimTittsler/Books/eXe<br />
    or http://wikieducator.org/WikiEducator:Collections/Cost_and_Finance_Unit_3</li>
  <li>Select the output format:<br />
  <input type="submit" value="Export IMS Content Package" name="imscp">most common LMS format for things like Moodle, ATutor, etc.<br />
  <input type="submit" value="Export IMS Common Cartridge" name="imscc">next generation packaging standard</li>
  <li>Upload the resulting package (.zip file) to your LMS.</li>
</ol>
</form>
<p class="version">Script version: 2012-10-28 15:45:15</p>
</body>
</html>
'''

nodes = []
class Node(object):
    def __init__(self, filename, title):
        global nodes
        self.id = 'RES-WE' + str(uuid4())
        self.filename = filename
        self.title = title
        self.resources = [self.filename, 'wikieducator.org.css']
        nodes.append(self)

class Manifest(object):
    def __init__(self, title, format=IMSCP):
        self.title = title
        self.format = format

    def write(self, pathname):
        global nodes
        f = open(pathname, 'wt')
        package_id = 'WE' + str(uuid1())
        organization_id = 'WE' + str(uuid4())
        if self.format == IMSCP:
            manifest_prologue = u'''<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="%s"
        xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
        xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2" 
        xmlns:imsmd="http://www.imsglobal.org/xsd/imsmd_v1p2" 
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
        xsi:schemaLocation="http://www.imsglobal.org/xsd/imscp_v1p1 imscp_v1p1.xsd http://www.imsglobal.org/xsd/imsmd_v1p2 imsmd_v1p2p2.xsd"> 
<metadata> 
 <schema>IMS Content</schema> 
 <schemaversion>1.1.3</schemaversion> 
 <adlcp:location>dublincore.xml</adlcp:location>
</metadata>
<organizations default="%s">
<organization identifier="%s" structure="hierarchical">
<title>%s</title>
''' % (package_id, organization_id, organization_id, self.title)
        elif self.format == SCORM12:
            manifest_prologue = u'''<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="%s"
        xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
        xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2" 
        xmlns:imsmd="http://www.imsglobal.org/xsd/imsmd_v1p2" 
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
        xsi:schemaLocation="http://www.imsglobal.org/xsd/imscp_v1p1 imscp_v1p1.xsd http://www.imsglobal.org/xsd/imsmd_v1p2 imsmd_v1p2p2.xsd"> 
<metadata> 
 <schema>IMS Content</schema> 
 <schemaversion>1.1.3</schemaversion> 
 <adlcp:location>dublincore.xml</adlcp:location>
</metadata>
<organizations default="%s">
<organization identifier="%s" structure="hierarchical">
<title>%s</title>
''' % (package_id, organization_id, organization_id, self.title)
        elif self.format == IMSCC:
            manifest_prologue = u'''<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="%s"
 xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:schemaLocation="http://www.imsglobal.org/xsd/imscc/imscp_v1p1 imscp_v1p1.xsd">
<metadata>
  <schema>IMS Common Cartridge</schema>
  <schemaversion>1.0.0</schemaversion>
  <lom xmlns="http://ltsc.ieee.org/xsd/imscc/LOM">
    <general>
      <title><string>WikiEducator Content</string></title>
      <description><string>A snapshot of content developed on WikiEducator.org.</string></description>
    </general>
    <technical>
      <format>text/html</format>
    </technical>
    <rights>
      <copyrightAndOtherRestrictions>
        <value>yes</value>
      </copyrightAndOtherRestrictions>
      <description><string>Creative Commons Attribution Share-Alike</string></description>
    </rights>
  </lom>
</metadata>
<organizations default="%s">
<organization identifier="%s" structure="hierarchical">
<title>%s</title>
''' % (package_id, organization_id, organization_id, self.title)
        else:
            pass

        f.write(manifest_prologue.encode('utf-8'))
        for node in nodes:
            item_id = 'ITEM-WE' + str(uuid4())
            f.write('  <item identifier="%s" isvisible="true" identifierref="%s">\n'
                   % (item_id, node.id))

            f.write('    <title>%s</title>\n' % node.title)
            f.write('  </item>\n')
        f.write('</organization>\n')
        f.write('</organizations>\n')
        f.write('<resources>\n')
        for node in nodes:
            f.write('  <resource identifier="%s" type="webcontent" href="%s">\n' % (node.id, node.filename))
            for file in node.resources:
                f.write('    <file href="%s"/>\n' % file)
            f.write('  </resource>\n')
        f.write('</resources>\n')
        f.write('</manifest>\n')
        f.close()

def url_join(a, b):
    url = a
    if not a.endswith('/'):
        url += '/'
    if b.startswith('/'):
        url += b[1:]
    else:
        url += b
    return url

def page_name(a, suffix=''):
    """make filesystem name based on unquoted base part of URL"""
    pn = unquote(a.split('/')[-1])
    if suffix <> '' and not pn.endswith(suffix):
        pn += suffix
    return cgi.escape(pn, True)

form = cgi.FieldStorage()
print "Content-Type: text/html"
print

if not form.has_key('url'):
    show_form()
    sys.exit()
if not (form.has_key('imscp') or form.has_key('imscc')):
    show_form(message="no submit")
    sys.exit()

url = form['url'].value

if not url.startswith('http://'):
    url = 'http://' + url
urlre = re.match(r'(?i)(?P<base>http://([^/]+\.)?wikieducator\.org).*', url)
if not urlre:
    show_form(message="URL must point to a WikiEducator collection")
    sys.exit(1)
base_url = urlre.group('base')

if form.has_key('imscp'):
    format = IMSCP
elif form.has_key('imscc'):
    format = IMSCC
else:
    show_form(message='unknown format requested')
    sys.exit()

temp_dir = mkdtemp('.we')
html_prologue = u'''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
<title>WikiEducator Content</title>
<style type="text/css">
@import url(wikieducator.org.css);
</style>%s
</head>
<body>
'''
html_epilogue = '''</body></html>
'''
#print "temp_dir", temp_dir
#base_url = 'http://wikieducator.org/'
#format = IMSCC
#url = os.path.join(base_url, 'User:JimTittsler/Collections/exe')
#url = os.path.join(base_url, 'WikiEducator:Collections/Cost_and_Finance_Unit_3')
collection = urllib2.urlopen(url)
soup = BeautifulSoup(collection)

# make sure the URL is a collection, and not a "page not found" page
if not soup.find('div', {'class': 'saved_book_heading'}):
    show_form(message='missing or malformed collection page')
    sys.exit()
if not soup.find('dl'):
    show_form(message='missing collection of pages (dl)')
    sys.exit()

ctitle = soup.find('span', {'class': 'mw-headline'})
if ctitle:
    collection_title = unicode(ctitle.string).strip()
else:
    collection_title = 'WikiEducator Resource'

print '''<html>
  <head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <title>%s -- WikiEducator</title>
</head><body><h1>Building package...</h1><ul>''' % cgi.escape(collection_title.encode('utf-8'))
sys.stdout.flush()

for page in soup('dd'):
    if not page.a:
        continue
    print '<li>',page.a.string,'</li>'
    page_url = url_join(base_url, page.a['href'])
    #print page_url,"</li>"
    sys.stdout.flush()
    p1 = urllib2.urlopen(page_url)
    p1_soup = BeautifulSoup(p1)
    embedded_styles = ''
    for stylesheet in p1_soup.findAll('style'):
        style = unicode(stylesheet)
        if '@import' not in style:
            embedded_styles += style
    sys.stdout.flush()
    #print p1_soup.find(id = 'bodyContent')
    body = p1_soup.find(id = 'bodyContent')
    # remove some bits
    body.find(id = 'siteSub').extract()
    body.find(id = 'contentSub').extract()
    body.find(id = 'jump-to-nav').extract()
    if body.find(id = 'toc'):
        body.find(id = 'toc').extract()
    if body.find(id = 'printfooter'):
        body.find(id = 'printfooter').extract()
    if body.find('div', {'class': 'navigation'}):
        body.find('div', {'class': 'navigation'}).extract()
    if body.find('table', {'class': re.compile(r'.*navigation.*')}):
        body.find('table', {'class': re.compile(r'.*navigation.*')}).extract()
    if body.find('div', {'class': 'printfooter'}):
        body.find('div', {'class': 'printfooter'}).extract()
    if body.find('table', {'class': 'workinprogress'}):
        body.find('table', {'class': 'workinprogress'}).extract()
    if body.find(id = 'catlinks'):
        body.find(id = 'catlinks').extract()
    # disable local links
    for link in body.findAll('a'):
        if not link.has_key('class'):
            #print "      classless link:", link
            if link.has_key('name'):
                continue
            tag = Tag(soup, 'span', [('class', 'removed_link')])
            tag.insert(0, link.contents[0])
            link.replaceWith(tag)
        elif link['class'].find('external') > -1:
            link['target'] = '_blank'
        elif link['class'].find('image') > -1:
            #print "      image link:", link
            tag = Tag(soup, 'span', [('class', 'removed_img_link')])
            tag.insert(0, link.contents[0])
            link.replaceWith(tag)
        else:
            #print "      non-ext link:",link
            tag = Tag(soup, 'span', [('class', 'removed_link')])
            tag.insert(0, link.contents[0])
            link.replaceWith(tag)
    node = Node(page_name(page_url, '.html'),
            os.path.basename(str(p1_soup.find('h1', {'class':'firstHeading'}).string).strip()))
    # fetch all the images
    for img in body.findAll('img'):
        img_url = str(img['src'])
        if not img_url.startswith('http://'):
            img_url = url_join(base_url, img_url)
        #print "  ", img_url
        img_contents = urllib2.urlopen(img_url)
        open(os.path.join(temp_dir, page_name(img_url)), 'wb').write(img_contents.read())
        img['src'] = page_name(img_url).decode('utf-8')
        node.resources.append(page_name(img_url))
        #print "    ", img
    # fetch all the movies
    # FIXME - does not fix up the embed tags
    for img in body.findAll('param', {'name':'movie'}):
        img_url = str(img['value'])
        if not img_url.startswith('http://'):
            img_url = url_join(base_url, img_url)
        #print "  ", img_url
        # disable fetching movies  2008-10-20
        if 0:
                img_contents = urllib2.urlopen(img_url)
                open(os.path.join(temp_dir, page_name(img_url)), 'wb').write(img_contents.read())
                img['value'] = page_name(img_url)
                node.resources.append(page_name(img_url))
                #print "    ", img
    f = open(os.path.join(temp_dir, page_name(page_url, '.html')), 'wt')
    head = html_prologue % embedded_styles
    f.write(head.encode('utf-8'))
    f.write(body.prettify())
    f.write(html_epilogue)
    f.close()
print "</ul>"
manifest = Manifest(collection_title, format)
manifest.write(os.path.join(temp_dir, 'imsmanifest.xml'))

# boilerplate files
if format == IMSCP:
    files = glob.glob(os.path.join(templates_directory, 'imscp/*'))
elif format == SCORM12:
    files = glob.glob(os.path.join(templates_directory, 'scorm12/*'))
elif format == IMSCC:
    files = glob.glob(os.path.join(templates_directory, 'imscc/*'))

for file in files:
    shutil.copy(file, temp_dir)

zip_dir = mkdtemp('.wikieducator', '', zips_directory)
zip_name = re.sub(r'[ /:@<>"]', u'_', collection_title).encode('utf-8') + '.zip'
zip_path = os.path.join(zip_dir, zip_name)
z = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
for file in glob.glob(os.path.join(temp_dir, '*')):
    z.write(file, os.path.basename(file))
z.close()
shutil.rmtree(temp_dir, ignore_errors = True)
print '<p>Download <a href="%s/%s/%s">%s</a></p>' % (
    download_url, os.path.basename(zip_dir), zip_name, zip_name)
print "</body></html>"


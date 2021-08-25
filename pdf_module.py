import os
import re
import zipfile
from io import BytesIO

import lxml.etree as ET
import pdfkit


class File_Resolver(ET.Resolver):
    def resolve(self, url, pubid, context):
        return self.resolve_filename(url, context)


class Pdf_Printer:
    def __init__(self):
        self.parser = ET.XMLParser()
        self.resolver = File_Resolver()
        self.parser.resolvers.add(File_Resolver())

    def get_xml(self, files_path):
        with zipfile.ZipFile(files_path, "r") as zfile:
            for name in zfile.namelist():
                if re.search(r"\.zip$", name) is not None:
                    # zip within a zip
                    zfiledata = BytesIO(zfile.read(name))
                    with zipfile.ZipFile(zfiledata) as zfile2:
                        for name2 in zfile2.namelist():
                            if ".xml" in name2:
                                with zfile2.open(name2) as xml:
                                    xml = xml.read()

                                return xml

    def get_html(self, xml=None):
        if b"KVZU" in xml:
            xsl_path = r"xml\zu\zu.xsl"
        elif b"KVOKS" in xml:
            xsl_path = r"xml\oks\oks.xsl"
        elif b"KPOKS" in xml:
            xsl_path = r"xml\room\room.xsl"
        else:
            return "Format not supported"

        xml_input = ET.fromstring(xml, self.parser)
        with open(xsl_path, "r", encoding="UTF-8") as xsl:
            xslt_root = ET.parse(xsl, self.parser)
        transform = ET.XSLT(xslt_root)
        html_string = str(transform(xml_input))

        return html_string

    def get_pdf(self, html_string=None):
        options = {
            "page-size": "A4",
            "margin-top": "1cm",
            "margin-right": "1cm",
            "margin-bottom": "1cm",
            "margin-left": "1cm",
            "encoding": "UTF-8",
            "orientation": "landscape",
            "print-media-type": None,
            "no-outline": None,
            "custom-header": [("Accept-Encoding", "gzip")],
        }

        pdf_document = pdfkit.from_string(html_string, False, options=options)

        return pdf_document

    def get_document(self, files_path=None, format=".pdf"):
        xml = self.get_xml(files_path)
        if format == ".xml":
            return xml
        html = self.get_html(xml)
        pdf = self.get_pdf(html)
        return pdf


pm = Pdf_Printer()

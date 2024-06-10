"""
    Flowblade Movie Editor is a nonlinear video editor.
    Copyright 2012 Janne Liljeblad.

    This file is part of Flowblade Movie Editor <https://github.com/jliljebl/flowblade/>.

    Flowblade Movie Editor is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Flowblade Movie Editor is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Flowblade Movie Editor.  If not, see <http://www.gnu.org/licenses/>.
"""

"""
Module contains absolute paths to various resources.
"""

ROOT_PATH = None

BLACK_IMAGE_PATH = None
IMAGE_PATH = None
PROFILE_PATH = None
PREFS_PATH = None
WIPE_RESOURCES_PATH = None
FILTERS_XML_DOC = None
COMPOSITORS_XML_DOC = None
REPLACEMENTS_XML_DOC = None
HELP_DOC = None
GPL_3_DOC = None
TRANSLATIONS_DOC = None
DEVELOPERS_DOC = None
CONTRIBUTORS_DOC = None
LOCALE_PATH = None
ROOT_PARENT = None
PATTERN_PRODUCER_PATH = None
LAUNCH_DIR = None
GMIC_SCRIPTS_DOC = None
PHANTOM_JAR = None
FLUXITY_EMPTY_BG_RES_PATH = None
MEDIA_PLUGINS_PATH = None
FLUXITY_API_DOC = None
USBHID_DRIVERS_PATH = None
INFO_TIPS_DOC = None


def set_paths(root_path):
    # Apr-2017 - SvdB - Added SHORTCUTS_PATH for keyboard shortcuts files
    global ROOT_PATH, IMAGE_PATH, THUMBNAIL_PATH, PROFILE_PATH,\
    BLACK_IMAGE_PATH, FILTERS_XML_DOC, COMPOSITORS_XML_DOC, \
    WIPE_RESOURCES_PATH, PREFS_PATH, HELP_DOC, LOCALE_PATH, \
    GPL_3_DOC, ROOT_PARENT, PATTERN_PRODUCER_PATH, TRANSLATIONS_DOC, \
    LAUNCH_DIR, REPLACEMENTS_XML_DOC, GMIC_SCRIPTS_DOC,  \
    PHANTOM_JAR, PHANTOM_DIR, DEVELOPERS_DOC, CONTRIBUTORS_DOC, \
    SHORTCUTS_PATH, FLUXITY_EMPTY_BG_RES_PATH, MEDIA_PLUGINS_PATH, \
    FLUXITY_API_DOC, USBHID_DRIVERS_PATH, INFO_TIPS_DOC

    ROOT_PATH = root_path
    IMAGE_PATH = ROOT_PATH + "/res/darktheme/"
    WIPE_RESOURCES_PATH = root_path + "/res/filters/wipes/"
    PROFILE_PATH = root_path + "/res/profiles/"
    BLACK_IMAGE_PATH = root_path + "/res/darktheme/black.jpg"
    FILTERS_XML_DOC = root_path + "/res/filters/filters.xml"
    COMPOSITORS_XML_DOC = root_path + "/res/filters/compositors.xml"
    REPLACEMENTS_XML_DOC = root_path + "/res/filters/replace.xml"
    PREFS_PATH = root_path + "/res/prefs/"
    HELP_DOC = root_path + "/res/help/help.html"
    LOCALE_PATH = root_path + "/locale/"
    GPL_3_DOC = root_path + "/res/help/gpl3"
    TRANSLATIONS_DOC = root_path + "/res/help/translations"
    DEVELOPERS_DOC = root_path + "/res/help/developers"
    CONTRIBUTORS_DOC = root_path + "/res/help/contributors"
    ROOT_PARENT = ROOT_PATH.strip("Flowblade")
    PATTERN_PRODUCER_PATH = root_path + "/res/patternproducer/"
    LAUNCH_DIR = root_path + "/launch/"
    GMIC_SCRIPTS_DOC = root_path + "/res/gmic/gmic2scripts.xml"
    PHANTOM_JAR = root_path + "/phantom2d/Phantom2D.jar"
    SHORTCUTS_PATH = root_path + "/res/shortcuts/"
    FLUXITY_EMPTY_BG_RES_PATH = root_path + "/res/scripttool/not_rendered.png"
    MEDIA_PLUGINS_PATH = root_path + "/res/mediaplugins/"
    FLUXITY_API_DOC = root_path + "/res/mediaplugins/fluxity.html"
    INFO_TIPS_DOC = root_path + "/res/help/en/infotips.html"
    USBHID_DRIVERS_PATH = root_path + "/res/usbhid/"
    
def apply_dark_theme():
    global IMAGE_PATH
    IMAGE_PATH = ROOT_PATH + "/res/darktheme/"




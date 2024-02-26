"""
    Flowblade Movie Editor is a nonlinear video editor.
    Copyright 2013 Janne Liljeblad.

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
    along with Flowblade Movie Editor. If not, see <http://www.gnu.org/licenses/>.
"""

import datetime

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import GdkPixbuf
from gi.repository import Pango

import appconsts
import dialogs
import dnd
import edit
import editorlayout
import guicomponents
import guipopover
import guiutils
import editorpersistance # Aug-2019 - SvdB - BB
import editorstate
from editorstate import PROJECT
import monitorevent
import render
import respaths
import updater
import utils


widgets = utils.EmptyClass()

do_multiple_clip_insert_func = None # this is monkeypathched here in app.py
log_changed_since_last_save = False

# Sort order
TIME_SORT = appconsts.TIME_SORT
NAME_SORT = appconsts.NAME_SORT
COMMENT_SORT = appconsts.COMMENT_SORT

sorting_order = TIME_SORT
_use_comments_for_name = False

# ----------------------------------- log data object
class MediaLogEvent:
    def __init__(self, event_type, mark_in, mark_out, name, path):
        self.event_type = event_type
        self.timestamp = datetime.datetime.now()
        self.mark_in = mark_in
        self.mark_out = mark_out
        self.name = name
        self.path = path
        self.comment = ""
        self.starred = False

    def get_event_name(self):
        if self.event_type == appconsts.MEDIA_LOG_INSERT:
            return "Insert"
        elif self.event_type == appconsts.MEDIA_LOG_MARKS_SET:
            return "Marks"

    def get_mark_in_str(self):
        return utils.get_tc_string(self.mark_in)

    def get_mark_out_str(self):
        return utils.get_tc_string(self.mark_out)
        
    def get_date_str(self):
        date_str = self.timestamp.strftime('%d %B, %Y - %H:%M')
        date_str = date_str.lstrip('0')
        return date_str

def _mark_log_changed():
    global log_changed_since_last_save
    log_changed_since_last_save = True

# ----------------------------------------------------------- dnd drop
def clips_drop(clips):
    for clip in clips:
        if clip.media_type == appconsts.VIDEO or clip.media_type == appconsts.AUDIO or clip.media_type == appconsts.IMAGE_SEQUENCE:
            if PROJECT().proxy_data.proxy_mode == appconsts.USE_ORIGINAL_MEDIA:
                clip_path = clip.path
            else:
                # We are in proxy mode, find out original media path
                media_item = PROJECT().get_media_file_for_path(clip.path)
                if media_item != None:
                    # 'media_item.second_file_path' points now to original media
                    # if proxy file exits.
                    clip_path = media_item.second_file_path
                    if clip_path == None:
                        # no proxy for this clip, use media from dragged clip
                        clip_path = clip.path
                else:
                    # no media item for this clip, use media from dragged clip
                    clip_path = clip.path

            log_event = MediaLogEvent(  appconsts.MEDIA_LOG_MARKS_SET,
                                        clip.clip_in,
                                        clip.clip_out,
                                        clip.name,
                                        clip.path)
            log_event.ttl = clip.ttl
            editorstate.PROJECT().media_log.append(log_event)
    _update_list_view(log_event)
    _mark_log_changed()

# ----------------------------------------------------------- gui events
def media_log_filtering_changed():
    widgets.media_log_view.fill_data_model()

def media_log_star_button_pressed():
    selected = widgets.media_log_view.get_selected_rows_list()
    log_events = get_current_filtered_events()
    for row in selected:
        index = max(row) # these are tuples, max to extract only value
        log_events[index].starred = True

    widgets.media_log_view.fill_data_model()
    _mark_log_changed()
    
def media_log_no_star_button_pressed():
    selected = widgets.media_log_view.get_selected_rows_list()
    log_events = get_current_filtered_events()
    for row in selected:
        index = max(row) # these are tuples, max to extract only value
        log_events[index].starred = False

    widgets.media_log_view.fill_data_model()
    _mark_log_changed()
    
def log_range_clicked():
    if editorstate.timeline_visible() == True:
        dialogs.no_timeline_ranges_dialog()
        return

    media_file = editorstate.MONITOR_MEDIA_FILE()
    if media_file == None:
        return
    if media_file.type == appconsts.PATTERN_PRODUCER:
        # INFOWINDOW ???
       return 
    if media_file.mark_in == -1 or media_file.mark_out == -1:
        return
    
    file_path = media_file.path
    if PROJECT().proxy_data.proxy_mode == appconsts.USE_PROXY_MEDIA:
        if media_file.second_file_path != None:
            file_path = media_file.second_file_path # proxy file exists
        else:
            file_path = media_file.path # no proxy file created
            
    log_event = MediaLogEvent(  appconsts.MEDIA_LOG_MARKS_SET,
                                media_file.mark_in,
                                media_file.mark_out,
                                media_file.name,
                                file_path)
    log_event.ttl = media_file.ttl

    editorstate.PROJECT().media_log.append(log_event)
    editorstate.PROJECT().add_to_group(_get_current_group_index(), [log_event])
    _update_list_view(log_event)
    _mark_log_changed()
    
def _update_list_view(log_event):
    widgets.media_log_view.fill_data_model()
    max_val = widgets.media_log_view.scroll.get_vadjustment().get_upper()
    editorlayout.show_panel(appconsts.PANEL_RANGE_LOG)
    view_group = get_current_filtered_events()
    try:
        event_index = view_group.index(log_event)
        widgets.media_log_view.treeview.get_selection().select_path(str(event_index))
    except:
        pass # if non-starred are not displayed currently. TODO: think of logic, should new items into displayed category?

    GLib.idle_add(_scroll_window, max_val)

def _scroll_window(max_val):
    widgets.media_log_view.scroll.get_vadjustment().set_value(max_val)
    return False

def log_item_name_edited(cell, path, new_text, user_data):
    if len(new_text) == 0:
        return

    item_index = int(path)
    current_view_events = get_current_filtered_events()
    current_view_events[item_index].comment = new_text
    tree_path = Gtk.TreePath.new_from_indices([item_index])
    iter = widgets.media_log_view.storemodel.get_iter(tree_path)
    widgets.media_log_view.storemodel.set_value (iter, 1, new_text)
    _mark_log_changed()
        
def delete_selected():
    selected = widgets.media_log_view.get_selected_rows_list()
    log_events = get_current_filtered_events()
    delete_events = []
    for row in selected:
        index = max(row) # these are tuple, max to extract only value
        delete_events.append(log_events[index])
        
    current_group_index = _get_current_group_index()
    if current_group_index != -1: # When user created group is displayed item is only deleted from that group
        PROJECT().remove_from_group(current_group_index, delete_events)
    else: # When "All Items" group is displayed item is deleted from "All Items" list and from all groups too  
        for i in range(0, len(PROJECT().media_log_groups)):
            PROJECT().remove_from_group(i, delete_events)
        PROJECT().delete_media_log_events(delete_events)

    widgets.media_log_view.fill_data_model()
    _mark_log_changed()
    
def display_item(row):
    log_events = get_current_filtered_events()
    event_item = log_events[row]
    media_file = PROJECT().get_media_file_for_path(event_item.path)
    media_file.mark_in = event_item.mark_in
    media_file.mark_out = event_item.mark_out
    updater.set_and_display_monitor_media_file(media_file)
    monitorevent.to_mark_in_pressed()

def log_list_view_button_press(treeview, event):
    path_pos_tuple = treeview.get_path_at_pos(int(event.x), int(event.y))
    if path_pos_tuple == None:
        return False
    if not (event.button == 3):
        return False

    path, column, x, y = path_pos_tuple
    selection = treeview.get_selection()
    selection.unselect_all()
    selection.select_path(path)
    row = int(max(path))

    guipopover.media_log_event_popover_show(row, treeview, event.x, event.y, _log_event_menu_item_selected)
    
    return True

def _log_event_menu_item_selected(action, variant, data):
    item_id, row, treeview = data
    
    if item_id == "delete":
        delete_selected()
    elif item_id == "toggle":
        log_events = get_current_filtered_events()
        log_events[row].starred = not log_events[row].starred 
        widgets.media_log_view.fill_data_model()
    elif item_id == "display":
        display_item(row)
    elif item_id == "renderslowmo":
        render_slowmo_from_item(row)

def _do_range_log_drop_on_monitor(row):
    display_item(row)

def _use_comments_toggled(action, variant, msg):
    new_state = not(action.get_state().get_boolean())
    action.set_state(GLib.Variant.new_boolean(new_state))
        
    global _use_comments_for_name
    _use_comments_for_name = new_state

def render_slowmo_from_item(row):
    log_events = get_current_filtered_events()
    event_item = log_events[row]
    media_file = PROJECT().get_media_file_for_path(event_item.path)
    media_file.mark_in = event_item.mark_in
    media_file.mark_out = event_item.mark_out
    render.render_frame_buffer_clip(media_file, True)

def get_current_filtered_events():   
    log_events = PROJECT().get_filtered_media_log_events(widgets.group_view_select.get_active() - 1,
                                                         widgets.star_check.get_active(),
                                                         widgets.star_not_active_check.get_active(),
                                                         sorting_order)
    return log_events

def _get_current_group_index():
    # Interpretation of returned values:
    # -1 is "All Items" group
    # 0 - n is group index in Project.media_log_groups list

    return widgets.group_view_select.get_active() - 1
    

def append_log_events():
    clips = []
    log_events = get_current_filtered_events()
    for le in log_events:
        clips.append(get_log_event_clip(le))
    
    track = editorstate.current_sequence().get_first_active_track()

    # Can't put audio media on video track
    for new_clip in clips:
        if ((new_clip.media_type == appconsts.AUDIO)
           and (track.type == appconsts.VIDEO)):
            dialogs.no_audio_dialog(track)
            return

    data = {"track":track,
            "clips":clips}

    action = edit.append_media_log_action(data)
    action.do_edit()

def insert_selected_log_events():
    clips = []
    log_events = get_current_filtered_events()
    
    treeselection = widgets.media_log_view.treeview.get_selection()
    (model, rows) = treeselection.get_selected_rows()
    
    for row_tuple in rows:
        row = row_tuple[0]
        le = log_events[row]
        clips.append(get_log_event_clip(le))
    
    track = editorstate.current_sequence().get_first_active_track()
    tline_pos = editorstate.current_tline_frame()
    do_multiple_clip_insert_func(track, clips, tline_pos)

def get_log_event_clip(log_event):
    # Versions before 1.16 do not have this attr in log_event objects
    if not hasattr(log_event, "ttl"):
        log_event.ttl = None

    # currently quaranteed not to be a pattern producer
    if PROJECT().proxy_data.proxy_mode == appconsts.USE_ORIGINAL_MEDIA:
        new_clip = editorstate.current_sequence().create_file_producer_clip(log_event.path, None, False, log_event.ttl)
    else:
        # We are in proxy mode, use proxy clip if available.
        media_item = PROJECT().get_media_file_for_second_path(log_event.path) # 'log_event.path' is always original media,
                                                                              # if we are in proxy mode we want to use proxy media if possible
        if media_item != None:
            new_clip = editorstate.current_sequence().create_file_producer_clip(media_item.path, None, False, log_event.ttl)
        else:
            new_clip = editorstate.current_sequence().create_file_producer_clip(log_event.path, None, False, log_event.ttl)
            
    # Set clip in and out points
    new_clip.clip_in = log_event.mark_in
    new_clip.clip_out = log_event.mark_out
    if _use_comments_for_name == True:
        new_clip.name = log_event.comment
        if len(new_clip.name) == 0:
            new_clip.name = log_event.name
    else:
        new_clip.name = log_event.name
    return new_clip

def get_clips_for_rows(rows):
    clips = []
    log_events = get_current_filtered_events()
    for row in rows:
        log_event = log_events[max(row)]
        clips.append(get_log_event_clip(log_event))      
        
    return clips

def display_log_clip_double_click_listener(treeview, path, view_column):
    row = int(max(path))
    data = ("display", row, treeview)
    _log_event_menu_item_selected(None, None, data)

def _group_action_pressed(launcher, widget, event, data):
    guipopover.range_log_hamburger_menu_show(launcher, widget, widgets.group_view_select.get_active() == 0, sorting_order, \
                                       _use_comments_for_name, PROJECT().media_log_groups,
                                        _actions_callback, _sorting_callback, _use_comments_toggled)

def _unsensitive_for_all_view(item):
    if widgets.group_view_select.get_active() == 0:
        item.set_sensitive(False)

def _actions_callback(action, variant, data):
    if data == "newfromselected":
        next_index = len(PROJECT().media_log_groups)
        dialogs.new_media_log_group_name_dialog(_new_group_name_callback, next_index, True)
    elif data == "new":
        next_index = len(PROJECT().media_log_groups)
        dialogs.new_media_log_group_name_dialog(_new_group_name_callback, next_index, False)
    elif data == "delete":
        current_group_index = _get_current_group_index()
        if current_group_index < 0:
            return
        PROJECT().media_log_groups.pop(current_group_index)
        _create_group_select()
        widgets.group_view_select.set_active(0)
    elif data == "rename":
        current_group_index = _get_current_group_index()
        name, items = PROJECT().media_log_groups[current_group_index]
        dialogs.group_rename_dialog(_rename_callback, name)
    else: # Move to group
        try:
            to_group_index = int(data)
        except:
            return

        current_group_index = _get_current_group_index()

        if to_group_index == current_group_index:
            return

        # Get items to move
        selected = widgets.media_log_view.get_selected_rows_list()
        log_events = get_current_filtered_events()
        move_items = []
        for row in selected:
            index = max(row) # these are tuples, max to extract only value
            move_items.append(log_events[index])

        # Move items and update
        PROJECT().remove_from_group(current_group_index, move_items)
        current_group_index = _get_current_group_index()
        PROJECT().add_to_group(to_group_index, move_items)
        widgets.group_view_select.set_active(to_group_index + 1) # 0 index items is "All" items group not a user created group

def _sorting_callback(action, variant):
    action.set_state(variant)
    print(variant.get_string())
    _sorting_changed(variant.get_string())
    guipopover._range_log_popover.hide()

def _delete_with_items_dialog_callback(dialog, response_id):
    dialog.destroy()
    if response_id != Gtk.ResponseType.ACCEPT:
        return
    
    current_group_index = _get_current_group_index()
    name, items = PROJECT().media_log_groups[current_group_index]
    PROJECT().delete_media_log_events(items)
    PROJECT().media_log_groups.pop(current_group_index)
    _create_group_select()
    widgets.group_view_select.set_active(0)
    _mark_log_changed()
        
def _rename_callback(dialog, response_id, entry):
    new_name = entry.get_text()
    dialog.destroy()
    if response_id == Gtk.ResponseType.CANCEL:
        return
    if len(new_name) == 0:
        return
        
    current_group_index = _get_current_group_index()
    old_name, items = PROJECT().media_log_groups[current_group_index]

    PROJECT().media_log_groups.pop(current_group_index)
    PROJECT().media_log_groups.insert(current_group_index, (new_name, items))
    _create_group_select()
    widgets.group_view_select.set_active(current_group_index + 1)
    _mark_log_changed()
    
def _viewed_group_changed(widget):
    update_media_log_view()

def _new_group_name_callback(dialog, response_id, data):
    if response_id == Gtk.ResponseType.CANCEL:
        dialog.destroy()
        return
    
    # Get group name and create type
    name_entry, add_selected = data
    new_name = name_entry.get_text()
    dialog.destroy()
    if len(new_name) == 0:
        new_name = _("Group ") + str(len(PROJECT().media_log_groups))

    # Add items to new group if requested
    items = []
    if add_selected:
        selected = widgets.media_log_view.get_selected_rows_list()
        log_events = get_current_filtered_events()
        for row in selected:
            index = max(row) # these are tuples, max to extract only value
            items.append(log_events[index])

        current_group_index = _get_current_group_index()
        if current_group_index >= 0:
            PROJECT().remove_from_group(current_group_index, items)

    # Update view
    PROJECT().add_media_log_group(new_name, items)
    _create_group_select()
    widgets.group_view_select.set_active(len(PROJECT().media_log_groups))
    update_media_log_view()
    _mark_log_changed()
    
def _sorting_changed(msg):
    global sorting_order
    if msg == "time":
        sorting_order = TIME_SORT
    elif msg == "name":
        sorting_order = NAME_SORT
    else:# "comment"
        sorting_order = COMMENT_SORT

    media_log_filtering_changed()
    
# ------------------------------------------------------------ gui
def get_media_log_list_view():
    media_log_view = MediaLogListView()
    global widgets
    widgets.media_log_view = media_log_view
    return media_log_view

def update_media_log_view():
    widgets.media_log_view.fill_data_model()
    # Does not show last line, do we need timer?
    max_val = widgets.media_log_view.scroll.get_vadjustment().get_upper()
    widgets.media_log_view.scroll.get_vadjustment().set_value(max_val)

    
class MediaLogListView(Gtk.VBox):

    def __init__(self):
        GObject.GObject.__init__(self)
        
       # Datamodel: icon, text, text
        self.storemodel = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str, str, str, str)
 
        # Scroll container
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # View
        self.treeview = Gtk.TreeView(model=self.storemodel)
        self.treeview.set_headers_visible(True)
        tree_sel = self.treeview.get_selection()
        tree_sel.set_mode(Gtk.SelectionMode.MULTIPLE)
        #self.treeview.connect("button-press-event", log_list_view_button_press)
        #self.treeview.connect("row-activated", display_log_clip_double_click_listener)
                              
        # Column views
        self.icon_col_1 = Gtk.TreeViewColumn("icon1")
        self.icon_col_1.set_title(_("Star"))
        self.text_col_1 = Gtk.TreeViewColumn("text1")
        self.text_col_1.set_title(_("Event"))
        self.text_col_2 = Gtk.TreeViewColumn("text2")
        self.text_col_2.set_title(_("Comment"))
        self.text_col_3 = Gtk.TreeViewColumn("text3")
        self.text_col_3.set_title(_("File Name"))
        self.text_col_4 = Gtk.TreeViewColumn("text4")
        self.text_col_4.set_title(_("Mark In"))
        self.text_col_5 = Gtk.TreeViewColumn("text5")
        self.text_col_5.set_title(_("Mark Out"))
        self.text_col_6 = Gtk.TreeViewColumn("text6")
        self.text_col_6.set_title(_("Date"))
    
        # Cell renderers
        self.icon_rend_1 = Gtk.CellRendererPixbuf()
        self.icon_rend_1.props.xpad = 6

        self.text_rend_1 = Gtk.CellRendererText()
        self.text_rend_1.set_property("ellipsize", Pango.EllipsizeMode.END)

        self.text_rend_2 = Gtk.CellRendererText()
        self.text_rend_2.set_property("yalign", 0.0)
        self.text_rend_2.set_property("editable", True)
        self.text_rend_2.set_property("ellipsize", Pango.EllipsizeMode.END)
        self.text_rend_2.connect("edited", log_item_name_edited, (self.storemodel, 2))
                                 
        self.text_rend_3 = Gtk.CellRendererText()
        self.text_rend_3.set_property("yalign", 0.0)

        self.text_rend_4 = Gtk.CellRendererText()
        self.text_rend_4.set_property("yalign", 0.0)

        self.text_rend_5 = Gtk.CellRendererText()
        self.text_rend_5.set_property("yalign", 0.0)

        self.text_rend_6 = Gtk.CellRendererText()
        self.text_rend_6.set_property("yalign", 0.0)

        # Build column views
        self.icon_col_1.set_expand(False)
        self.icon_col_1.set_spacing(5)
        self.text_col_1.set_min_width(20)
        self.icon_col_1.pack_start(self.icon_rend_1, False)
        self.icon_col_1.add_attribute(self.icon_rend_1, 'pixbuf', 0)

        self.text_col_2.set_expand(True)
        self.text_col_2.set_sizing(Gtk.TreeViewColumnSizing.GROW_ONLY)
        self.text_col_2.set_min_width(250)
        self.text_col_2.pack_start(self.text_rend_2, True)
        self.text_col_2.add_attribute(self.text_rend_2, "text", 1)

        self.text_col_3.set_expand(True)
        self.text_col_3.pack_start(self.text_rend_3, True)
        self.text_col_3.add_attribute(self.text_rend_3, "text", 2)

        self.text_col_4.set_expand(True)
        self.text_col_4.pack_start(self.text_rend_4, True)
        self.text_col_4.add_attribute(self.text_rend_4, "text", 3)

        self.text_col_5.set_expand(True)
        self.text_col_5.pack_start(self.text_rend_5, True)
        self.text_col_5.add_attribute(self.text_rend_5, "text", 4)

        self.text_col_6.set_expand(True)
        self.text_col_6.pack_start(self.text_rend_6, True)
        self.text_col_6.add_attribute(self.text_rend_6, "text", 5)
        
        # Add column views to view
        self.treeview.append_column(self.icon_col_1)
        self.treeview.append_column(self.text_col_2)
        self.treeview.append_column(self.text_col_3)
        self.treeview.append_column(self.text_col_4)
        self.treeview.append_column(self.text_col_5)
        self.treeview.append_column(self.text_col_6)

        # Build widget graph and display
        self.scroll.add(self.treeview)
        self.pack_start(self.scroll, True, True, 0)
        
        guiutils.set_margins(self, 6, 6, 0, 0)
        self.scroll.show_all()

    def fill_data_model(self):
        self.storemodel.clear()
        star_icon_path = respaths.IMAGE_PATH + "star.png"
        no_star_icon_path = respaths.IMAGE_PATH + "star_not_active.png"

        log_events = get_current_filtered_events()
        for log_event in log_events:
            if log_event.starred == True:
                icon = GdkPixbuf.Pixbuf.new_from_file(star_icon_path)
            else:
                icon =  GdkPixbuf.Pixbuf.new_from_file(no_star_icon_path)
            row_data = [icon, 
                        log_event.comment,
                        log_event.name,
                        log_event.get_mark_in_str(),
                        log_event.get_mark_out_str(),
                        log_event.get_date_str()]
            self.storemodel.append(row_data)

        self.scroll.queue_draw()

    def get_selected_rows_list(self):
        model, rows = self.treeview.get_selection().get_selected_rows()
        return rows

def get_media_log_events_panel(events_list_view):
    global widgets

    group_actions_menu = guicomponents.HamburgerPressLaunch(_group_action_pressed)
    group_actions_menu.do_popover_callback = True
    guiutils.set_margins(group_actions_menu.widget, 10, 0, 2, 18)

    star_check = Gtk.CheckButton()
    star_check.set_active(True)
    star_check.connect("clicked", lambda w:media_log_filtering_changed())
    star_check.set_margin_end(5)
    widgets.star_check = star_check

    star_label = Gtk.Image()
    # Aug-2019 - SvdB - BB
    star_label.set_from_file(respaths.IMAGE_PATH + guiutils.get_image_name("star", double_height=editorpersistance.prefs.double_track_hights))

    star_not_active_check = Gtk.CheckButton()
    star_not_active_check.set_active(True)
    star_not_active_check.connect("clicked", lambda w:media_log_filtering_changed())
    star_not_active_check.set_margin_end(5)
    widgets.star_not_active_check = star_not_active_check

    star_not_active_label = Gtk.Image()
    # Aug-2019 - SvdB - BB
    star_not_active_label.set_from_file(respaths.IMAGE_PATH + guiutils.get_image_name("star_not_active", double_height=editorpersistance.prefs.double_track_hights))

    star_button = Gtk.Button()
    # Aug-2019 - SvdB - BB
    star_button.set_image(guiutils.get_image("star"))
    star_button.connect("clicked", lambda w: media_log_star_button_pressed())

    no_star_button = Gtk.Button()
    # Aug-2019 - SvdB - BB
    no_star_button.set_image(guiutils.get_image("star_not_active"))
    no_star_button.connect("clicked", lambda w: media_log_no_star_button_pressed())

    widgets.group_box = Gtk.HBox()
    _create_group_select()
    widgets.group_view_select.set_active(0)
    
    row1 = Gtk.HBox()
    row1.pack_start(guiutils.get_pad_label(6, 12), False, True, 0)
    row1.pack_start(guiutils.get_pad_label(6, 12), False, True, 0)
    row1.pack_start(widgets.group_box, False, True, 0)
    row1.pack_start(guiutils.get_pad_label(6, 12), False, True, 0)
    row1.pack_start(star_check, False, True, 0)
    row1.pack_start(star_label, False, True, 0)
    row1.pack_start(guiutils.get_pad_label(6, 12), False, True, 0)
    row1.pack_start(star_not_active_check, False, True, 0)
    row1.pack_start(star_not_active_label, False, True, 0)
    row1.pack_start(guiutils.pad_label(12, 12), False, False, 0)
    row1.pack_start(star_button, False, True, 0)
    row1.pack_start(no_star_button, False, True, 0)
    row1.pack_start(Gtk.Label(), True, True, 0)

    # Aug-2019 - SvdB - BB
    prefs = editorpersistance.prefs
    size_adj = 1
    if prefs.double_track_hights:
        size_adj = 2
    widgets.log_range = Gtk.Button()
    widgets.log_range.set_image(guiutils.get_image("log_range"))
    widgets.log_range.set_size_request(80, 30)
    widgets.log_range.connect("clicked", lambda w:log_range_clicked())

    delete_button = Gtk.Button()
    delete_button.set_image(guiutils.get_image("delete_log_range"))
    delete_button.set_size_request(80, 30)
    delete_button.connect("clicked", lambda w:delete_selected())

    insert_displayed = Gtk.Button()
    insert_displayed.set_image(guiutils.get_image("insert_media_log"))
    insert_displayed.set_size_request(80, 22)
    insert_displayed.connect("clicked", lambda w:insert_selected_log_events())

    append_displayed = Gtk.Button()
    append_displayed.set_image(guiutils.get_image("append_media_log"))
    append_displayed.set_size_request(80, 22)
    append_displayed.connect("clicked", lambda w:append_log_events())

    row2 =  Gtk.HBox()
    row2.pack_start(group_actions_menu.widget, False, True, 0)
    row2.pack_start(widgets.log_range, False, True, 0)
    row2.pack_start(delete_button, False, True, 0)
    row2.pack_start(Gtk.Label(), True, True, 0)
    row2.pack_start(insert_displayed, False, True, 0)
    row2.pack_start(append_displayed, False, True, 0)

    # NOTE: Panel width determined by row1 widgets sizes.
    panel = Gtk.VBox()
    panel.pack_start(row1, False, True, 0)
    panel.pack_start(events_list_view, True, True, 0)
    panel.pack_start(row2, False, True, 0)

    star_check.set_tooltip_text(_("Display starred ranges"))    
    star_not_active_check.set_tooltip_text(_("Display non-starred ranges"))
    star_button.set_tooltip_text(_("Set selected ranges starred"))
    no_star_button.set_tooltip_text(_("Set selected ranges non-starred"))
    widgets.log_range.set_tooltip_text(_("Log current marked Media Item range"))
    delete_button.set_tooltip_text(_("Delete selected ranges"))
    insert_displayed.set_tooltip_text(_("Insert selected ranges on Timeline"))
    append_displayed.set_tooltip_text(_("Append displayed ranges on Timeline"))

    dnd.connect_range_log(events_list_view.treeview, _do_range_log_drop_on_monitor)
        
    return panel

def update_group_select_for_load():
    _create_group_select()
    widgets.group_view_select.set_active(0)
    
def _create_group_select():
    try:
        widgets.group_box.remove(widgets.group_view_select)
    except:
        pass

    group_view_select = Gtk.ComboBoxText() # filled later when current sequence known
    group_view_select.append_text(_("All Items"))
    for group_data in PROJECT().media_log_groups:
        name, items = group_data
        group_view_select.append_text(name)

    group_view_select.set_size_request(250, 30)
    group_view_select.connect('changed', _viewed_group_changed)
    group_view_select.set_tooltip_text(_("Select viewed Range Log Items Group"))

    widgets.group_view_select = group_view_select
    widgets.group_box.add(widgets.group_view_select)
    widgets.group_view_select.show()

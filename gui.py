#!/usr/bin/env python

import argparse
import os
import shutil  # for copying files

import pysrt
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class SrtFile(object):
    SUPPORTED_EXTENSIONS = ("srt", "ssa", "ass", "idx")

    def __init__(self, is_good=False):
        self.filename = None
        self._basename = None
        self._extension = None
        self.is_good = is_good
        self.changed = False

    def set_filename(self, filename):
        try:
            basename, extension = os.path.splitext(filename)
            extension = extension[1:]
        except:
            return False, "Invalid file"  # case for .aaa? meh

        if extension not in self.SUPPORTED_EXTENSIONS:  # woot, this is super readable
            return False, "Not a valid subtitle file"

        self.filename = filename
        self._basename = basename
        self._extension = extension

        return True, ""

    def save_srt_to_file(self, srt_string):
        # create temp backup of file
        backup = self._basename + "-backup." + self._extension
        shutil.copyfile(self.filename, backup)
        print("Created backup at {}".format(backup))

        # print 'srt[100]: %s' % self.srt_string[:100]
        subs = pysrt.from_string(srt_string)
        subs.clean_indexes()
        subs.save(self.filename, encoding='utf-8')

        # TODO delete backup
        # print "Finished converting your file"


class Subfixer(object):
    def __init__(self, good_file=None, bad_file=None):
        self.alert_window = None
        self.basename = None
        self.extension = None
        self.srt_string = None

        self.model = Gtk.ListStore(int, str, str, str, str)
        self.view = None

        self.good_file = SrtFile(True)
        self.bad_file = SrtFile()

        self.is_good_selected, message = self.good_file.set_filename(good_file)
        if self.is_good_selected:
            self.load_srt(self.good_file)
        else:
            print(message)
        self.good_label = None

        self.is_bad_selected, message = self.bad_file.set_filename(bad_file)
        if self.is_bad_selected:
            self.load_srt(self.bad_file)
        else:
            print(message)
        self.bad_label = None

    def _add_files_widgets(self, hbox, is_good=True):
        vbox = Gtk.VBox()

        choose = Gtk.Button.new_with_label("Choose file")
        choose.is_good = is_good
        choose.connect("clicked", self.choose_clicked)
        vbox.pack_start(choose, True, True, 0)

        if is_good:
            self.good_label = Gtk.Label.new("File: %s" % self.good_file.filename)
            vbox.pack_start(self.good_label, True, True, 0)
        else:
            self.bad_label = Gtk.Label.new("File: %s" % self.bad_file.filename)
            vbox.pack_start(self.bad_label, True, True, 0)

        hbox.pack_start(vbox, True, True, 0)

    def create_main_window(self):
        columns = ['index', 'start', 'end', 'good', 'bad']

        window = Gtk.Window()
        vbox = Gtk.VBox()

        hbox = Gtk.HBox()
        vbox.pack_start(hbox, True, True, 0)

        self._add_files_widgets(hbox)
        self._add_files_widgets(hbox, False)

        view = Gtk.TreeView(model=self.model)
        # for each column
        for i, column in enumerate(columns):
            # cellrenderer to render the text
            cell = Gtk.CellRendererText()
            # the column is created
            col = Gtk.TreeViewColumn(column, cell, text=i)
            # and it is appended to the treeview
            view.append_column(col)

        view.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        view.set_size_request(1000, 600)

        scroll_tree = Gtk.ScrolledWindow()
        scroll_tree.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll_tree.add(view)

        self.view = view

        vbox.pack_start(scroll_tree, True, True, 0)

        hbox = Gtk.HBox()

        left_copy_btn = Gtk.Button.new_with_label("<--")
        left_copy_btn.connect("clicked", self.left_copy_clicked)
        hbox.pack_start(left_copy_btn, True, True, 0)

        merge_btn = Gtk.Button.new_with_label("Merge")
        merge_btn.connect("clicked", self.merge_clicked)
        hbox.pack_start(merge_btn, True, True, 0)

        right_copy_btn = Gtk.Button.new_with_label("-->")
        right_copy_btn.connect("clicked", self.right_copy_clicked)
        hbox.pack_start(right_copy_btn, True, True, 0)

        vbox.pack_start(hbox, True, True, 0)

        save_btn = Gtk.Button.new_with_label("Save")
        save_btn.connect("clicked", self.save_clicked)
        vbox.pack_start(save_btn, True, True, 0)

        window.set_size_request(1200, 800)
        window.set_title("SubsFixer")
        window.connect("destroy", self.quit)
        window.add(vbox)
        # self.window.add(self.text)
        # self.window.add(self.go)
        window.show_all()

    def destroy_alert(self, window):
        self.alert_window.destroy()

    @staticmethod
    def quit(event_source):
        Gtk.main_quit()

    def show_alert(self, alert_text):
        self.alert_window = Gtk.Dialog("Message", None, Gtk.DIALOG_MODAL | Gtk.DIALOG_DESTROY_WITH_PARENT)
        self.alert_window.vbox.add(Gtk.Label(alert_text))
        btn = Gtk.Button("OK")
        self.alert_window.vbox.add(btn)
        btn.connect("clicked", self.destroy_alert)
        self.alert_window.set_size_request(200, 100)
        self.alert_window.move(100, 200)
        self.alert_window.show_all()

    def _make_srt(self, _model, _path, _iter, column):
        text = _model.get_value(_iter, column)
        if text is not None:
            index = _model.get_value(_iter, 0)
            start = _model.get_value(_iter, 1)
            end = _model.get_value(_iter, 2)
            self.srt_string += '%d\n%s --> %s\n%s\n\n' % (index, start, end, text)

    def save_clicked(self, btn):
        if self.good_file.changed:
            self.srt_string = ''
            self.model.foreach(self._make_srt, 3)
            self.good_file.save_srt_to_file(self.srt_string)
            self.show_alert("File %s saved successfully" % self.good_file.filename)
            self.good_file.changed = False

        if self.bad_file.changed:
            self.srt_string = ''
            self.model.foreach(self._make_srt, 4)
            self.bad_file.save_srt_to_file(self.srt_string)
            self.show_alert("File %s saved successfully" % self.bad_file.filename)
            self.bad_file.changed = False

    def find_copy_paths(self, pathlist, column):
        shift_len = len(pathlist)

        # find first empty row
        srt_iter = self.model.get_iter(pathlist[0])
        value = None
        while srt_iter is not None:
            value = self.model.get_value(srt_iter, column)
            if value is None:
                break
            srt_iter_next = self.model.iter_next(srt_iter)
            if srt_iter_next is None:
                break
            srt_iter = srt_iter_next

        from_path = int(self.model.get_string_from_iter(srt_iter))
        to_path = int(self.model.get_string_from_iter(srt_iter)) + shift_len

        if value is None:
            from_path -= 1
            to_path -= 1

        from_iter = self.model.get_iter(from_path)
        srt_index = self.model.get_value(from_iter, 0)
        srt_start = self.model.get_value(from_iter, 1)
        srt_end = self.model.get_value(from_iter, 2)

        # add rows
        # print from_path, to_path, len(self.model)
        if to_path >= len(self.model):
            for _ in range(to_path - len(self.model) + 1):
                srt_index += 1
                self.model.append([srt_index, srt_start, srt_end, None, None])

        return from_path, to_path

    def left_copy_clicked(self, btn):
        # Copy selected lines to good file
        (model, pathlist) = self.view.get_selection().get_selected_rows()
        from_path, to_path = self.find_copy_paths(pathlist, 3)
        # print from_path, to_path, len(self.model)

        # shift rows
        # print from_path, pathlist[0][0]
        while from_path >= pathlist[0][0]:
            from_iter = model.get_iter(from_path)
            srt_start = model.get_value(from_iter, 1)
            srt_end = model.get_value(from_iter, 2)
            srt_text = model.get_value(from_iter, 3)
            to_iter = model.get_iter(to_path)
            model.set(to_iter, 1, srt_start, 2, srt_end, 3, srt_text)
            from_path -= 1
            to_path -= 1

        # clear selected rows
        from_iter = model.get_iter(pathlist[0])
        srt_start = model.get_value(from_iter, 1)
        srt_end = model.get_value(from_iter, 2)
        for path in pathlist:
            srt_iter = model.get_iter(path)
            model.set(srt_iter, 1, srt_start, 2, srt_end, 3, '')

        self.view.get_selection().unselect_all()
        self.good_file.changed = True

    def merge_clicked(self, btn):
        # merge selected lines in bad file
        (model, pathlist) = self.view.get_selection().get_selected_rows()
        shift_len = len(pathlist)

        # get lines to merge
        srt_list = []
        for path in pathlist:
            srt_iter = model.get_iter(path)
            srt_list.append(model.get_value(srt_iter, 4))
        srt_string = '\n'.join(srt_list)

        # update first selected row
        srt_iter = model.get_iter(pathlist[0])
        model.set_value(srt_iter, 4, srt_string)

        # move other rows
        srt_iter = model.iter_next(srt_iter)
        while srt_iter is not None:
            copy_path = int(model.get_string_from_iter(srt_iter)) + shift_len - 1
            try:
                copy_iter = model.get_iter(copy_path)
                value = model.get_value(copy_iter, 4)
                model.set_value(srt_iter, 4, value)
            except ValueError:
                # copy_path is bigger than max path
                model.set_value(srt_iter, 4, None)
            srt_iter = model.iter_next(srt_iter)

        self.view.get_selection().unselect_all()
        self.bad_file.changed = True

    def right_copy_clicked(self, btn):
        # Copy selected lines to bad file
        (model, pathlist) = self.view.get_selection().get_selected_rows()
        from_path, to_path = self.find_copy_paths(pathlist, 4)
        # print from_path, to_path, len(self.model)

        # shift rows
        # print from_path, pathlist[0][0]
        while from_path >= pathlist[0][0]:
            from_iter = model.get_iter(from_path)
            srt_text = model.get_value(from_iter, 4)
            to_iter = model.get_iter(to_path)
            model.set(to_iter, 4, srt_text)
            from_path -= 1
            to_path -= 1

        # clear selected rows
        for path in pathlist:
            srt_iter = model.get_iter(path)
            srt_text = model.get_value(srt_iter, 3)
            model.set(srt_iter, 4, srt_text)

        self.view.get_selection().unselect_all()
        self.bad_file.changed = True

    def load_srt(self, srt_file):
        srt_list = pysrt.open(srt_file.filename)
        # print len(srt_list)

        # Add rows to the model
        for i, sub in enumerate(srt_list):
            if srt_file.is_good:
                text_column = 3
                good_text = sub.text
                bad_text = None
            else:
                text_column = 4
                good_text = None
                bad_text = sub.text

            try:
                srt_iter = self.model.get_iter(i)
                self.model.set_value(srt_iter, text_column, sub.text)
            except ValueError:
                self.model.append([sub.index, sub.start, sub.end, good_text, bad_text])

    def choose_clicked(self, btn):
        self.extension = ""
        if btn.is_good:
            label = self.good_label
            srt_file = self.good_file
        else:
            label = self.bad_label
            srt_file = self.bad_file
        label.set_text("File: None")

        chooser_dialog = Gtk.FileChooserDialog("Open file", btn.get_toplevel(), Gtk.FILE_CHOOSER_ACTION_OPEN)
        chooser_dialog.add_button(Gtk.STOCK_CANCEL, 0)
        chooser_dialog.add_button(Gtk.STOCK_OPEN, 1)
        chooser_dialog.set_default_response(1)

        if chooser_dialog.run() == 1:
            # print chooser_dialog.get_filename()
            filepath = chooser_dialog.get_filename()
            chooser_dialog.destroy()

            selected, message = srt_file.set_filename(filepath)
            if not selected:
                self.show_alert(message)
                return

            self.load_srt(srt_file)

            if btn.is_good:
                self.is_good_selected = True
            else:
                self.is_bad_selected = True

            label.set_text("File: %s" % srt_file.filename)
            print("FILE SELECTED")
        else:
            chooser_dialog.destroy()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--good')
    parser.add_argument('--bad')
    args = parser.parse_args()

    subfixer = Subfixer(good_file=args.good, bad_file=args.bad)
    subfixer.create_main_window()
    Gtk.main()

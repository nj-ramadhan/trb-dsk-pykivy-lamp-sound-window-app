from kivy.clock import Clock
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivymd.font_definitions import theme_font_styles
from kivymd.uix.datatables import MDDataTable
from kivy.uix.screenmanager import ScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp
from kivy.metrics import dp
from kivymd.toast import toast
import numpy as np
import time
import os
import pyaudio
from math import log10
import audioop  
import mysql.connector
from escpos.printer import Serial as printerSerial
import configparser
import serial.tools.list_ports as ports
import hashlib
import serial

from shared import *

class ScreenHLM(MDScreen):        
    def __init__(self, **kwargs):
        super(ScreenHLM, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init, 2)
        
    def delayed_init(self, dt):
        pass

    def reset_data(self):
        global count_starting, count_get_data, dt_hlm_value

        count_starting = 3
        count_get_data = 4
        dt_hlm_value = 0.0

    def exec_start(self):
        global flag_play
        screen_main = self.screen_manager.get_screen('screen_main')
        self.reset_data()
        if(not flag_play):
            #stream.start_stream()
            #Clock.schedule_interval(screen_main.regular_get_data_slm, 1)
            flag_play = True

    def exec_reload(self):
        global flag_play, stream

        screen_main = self.screen_manager.get_screen('screen_main')
        self.reset_data()
        self.ids.bt_reload.disabled = True

        if(not flag_play):
            stream.start_stream()
            Clock.schedule_interval(screen_main.regular_get_data_hlm, 1)
            flag_play = True

    def exec_save(self):
        global flag_play
        global count_starting, count_get_data
        global mydb, db_antrian
        global dt_no_antrian, dt_no_reg, dt_no_uji, dt_nama, dt_jenis_kendaraan
        global dt_hlm_flag, dt_hlm_value, dt_hlm_user, dt_hlm_post
        global printer

        try:

            self.ids.bt_save.disabled = True

            mycursor = mydb.cursor()

            sql = "UPDATE tb_cekident SET hlm_flag = %s, hlm_value = %s, hlm_user = %s, hlm_post = %s WHERE noantrian = %s"
            sql_hlm_flag = (1 if dt_hlm_flag == "Lulus" else 2)
            dt_hlm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
            print_datetime = str(time.strftime("%d %B %Y %H:%M:%S", time.localtime()))
            sql_val = (sql_hlm_flag, dt_hlm_value, dt_hlm_user, dt_hlm_post, dt_no_antrian)
            mycursor.execute(sql, sql_val)
            mydb.commit()

            printer.set(align="center", normal_textsize=True)
            printer.image("asset/logo-dishub-print.png")
            printer.ln()
            printer.textln("HASIL UJI LEVEL KEBISINGAN KLAKSON KENDARAAN")
            printer.set(bold=True)
            printer.textln(f"Tanggal: {print_datetime}")
            printer.textln("=======================================")
            printer.set(align="left", normal_textsize=True)
            printer.textln(f"No Antrian: {dt_no_antrian}")
            printer.text(f"No Reg: {dt_no_reg}\t")
            printer.textln(f"No Uji: {dt_no_uji}")
            printer.textln(f"Nama: {dt_nama}")
            printer.textln(f"Jenis Kendaraan: {dt_jenis_kendaraan}")
            printer.textln("  ")
            printer.set(double_height=True, double_width=True)
            printer.text(f"Status:\t")
            printer.set(bold=True)
            printer.textln(f"{dt_slm_flag}")
            printer.set(bold=False)
            printer.text(f"Nilai:\t")
            printer.set(bold=True)
            printer.textln(f"{str(np.round(dt_slm_value, 2))}")
            printer.set(align="center", normal_textsize=True)     
            printer.textln("  ")
            printer.image("asset/logo-trb-print.png")
            printer.cut()

            self.open_screen_main()

        except Exception as e:
            toast_msg = f'error Save Data: {e}'
            toast(toast_msg) 

    def open_screen_main(self):
        global flag_play      

        screen_main = self.screen_manager.get_screen('screen_main')
        self.reset_data()
        flag_play = False  
        screen_main.exec_reload_table()
        self.screen_manager.current = 'screen_main'

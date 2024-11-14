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

class ScreenWTM(MDScreen):        
    def __init__(self, **kwargs):
        super(ScreenWTM, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init, 2)
        #
    def delayed_init(self, dt):
        pass

    def exec_start(self):
        global flag_play, stream
        global count_starting, count_get_data

        screen_main = self.screen_manager.get_screen('screen_main')

        count_starting = 3
        count_get_data = 10

        if(not flag_play):
            stream.start_stream()
            Clock.schedule_interval(screen_main.regular_get_data_wtm, 1)
            flag_play = True

    def exec_reload(self):
        global flag_play
        global count_starting, count_get_data, dt_wtm_value

        screen_main = self.screen_manager.get_screen('screen_main')

        count_starting = 3
        count_get_data = 10
        dt_wtm_value = 0
        self.ids.bt_reload.disabled = True
        self.ids.lb_window_tint.text = "..."

        if(not flag_play):
            stream.start_stream()
            Clock.schedule_interval(screen_main.regular_get_data_wtm, 1)
            flag_play = True

    def exec_save(self):
        global flag_play
        global count_starting, count_get_data
        global mydb, db_antrian
        global dt_no_antrian, dt_no_reg, dt_no_uji, dt_nama, dt_jenis_kendaraan
        global dt_wtm_flag, dt_wtm_value, dt_wtm_user, dt_wtm_post
        global printer

        try:
            self.ids.bt_save.disabled = True

            mycursor = mydb.cursor()

            sql = "UPDATE tb_cekident SET wtm_flag = %s, wtm_value = %s, wtm_user = %s, wtm_post = %s WHERE noantrian = %s"
            sql_wtm_flag = (1 if dt_wtm_flag == "Lulus" else 2)
            dt_wtm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
            print_datetime = str(time.strftime("%d %B %Y %H:%M:%S", time.localtime()))
            sql_val = (sql_wtm_flag, dt_wtm_value, dt_wtm_user, dt_wtm_post, dt_no_antrian)
            mycursor.execute(sql, sql_val)
            mydb.commit()

            printer.set(align="center", normal_textsize=True)
            printer.image("assets/logo-dishub-print.png")
            printer.ln()
            printer.textln("HASIL UJI TINGKAT PENERUSAN CAHAYA KACA KENDARAAN")
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
            printer.textln(f"{dt_wtm_flag}")
            printer.set(bold=False)
            printer.text(f"Nilai:\t")
            printer.set(bold=True)
            printer.textln(f"{str(np.round(dt_wtm_value, 2))}")
            printer.set(align="center", normal_textsize=True)     
            printer.textln("  ")
            printer.image("assets/logo-trb-print.png")
            printer.cut()

            self.open_screen_main()
        
        except Exception as e:
            toast_msg = f'error Save Data: {e}'
            toast(toast_msg) 

    def open_screen_main(self):
        global flag_play        
        global count_starting, count_get_data

        screen_main = self.screen_manager.get_screen('screen_main')

        count_starting = 3
        count_get_data = 10
        flag_play = False   
        screen_main.exec_reload_table()
        Clock.unschedule(screen_main.regular_get_data_wtm)
        self.screen_manager.current = 'screen_main'

    def exec_logout(self):
        self.screen_manager.current = 'screen_login'

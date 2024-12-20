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
import configparser
import serial.tools.list_ports as ports
import hashlib
import serial

colors = {
    "Red": {
        "A200": "#FF2A2A",
        "A500": "#FF8080",
        "A700": "#FFD5D5",
    },

    "Gray": {
        "200": "#CCCCCC",
        "500": "#ECECEC",
        "700": "#F9F9F9",
    },

    "Blue": {
        "200": "#4471C4",
        "500": "#5885D8",
        "700": "#6C99EC",
    },

    "Green": {
        "200": "#2CA02C", #41cd93
        "500": "#2DB97F",
        "700": "#D5FFD5",
    },

    "Yellow": {
        "200": "#ffD42A",
        "500": "#ffE680",
        "700": "#fff6D5",
    },

    "Light": {
        "StatusBar": "E0E0E0",
        "AppBar": "#202020",
        "Background": "#EEEEEE",
        "CardsDialogs": "#FFFFFF",
        "FlatButtonDown": "#CCCCCC",
    },

    "Dark": {
        "StatusBar": "101010",
        "AppBar": "#E0E0E0",
        "Background": "#111111",
        "CardsDialogs": "#222222",
        "FlatButtonDown": "#DDDDDD",
    },
}

#load credentials from config.ini
config = configparser.ConfigParser()
config.read('config.ini')
DB_HOST = config['mysql']['DB_HOST']
DB_USER = config['mysql']['DB_USER']
DB_PASSWORD = config['mysql']['DB_PASSWORD']
DB_NAME = config['mysql']['DB_NAME']
TB_DATA = config['mysql']['TB_DATA']
TB_USER = config['mysql']['TB_USER']

TB_MEASURE_HLM = config['mysql']['TB_MEASURE_HLM']

STANDARD_MIN_HLM = float(config['standard']['STANDARD_MIN_HLM']) # in lumen
STANDARD_MIN_SLM = float(config['standard']['STANDARD_MIN_SLM']) # in dbm
STANDARD_MAX_SLM = float(config['standard']['STANDARD_MAX_SLM']) # in dbm
STANDARD_MIN_WTM = float(config['standard']['STANDARD_MIN_WTM']) # in %

COM_PORT_WTM = config['device']['COM_PORT_WTM']

COUNT_STARTING = 3
COUNT_ACQUISITION = 4
TIME_OUT = 500

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 0.8
WIDTH = 2

db_slm_value = np.array([0.0])
dt_slm_value = 0
dt_slm_flag = 0
dt_slm_user = 1
dt_slm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
db_hlm_value = 0
dt_hlm_value = 0
dt_hlm_flag = 0
dt_hlm_user = 1
dt_slm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
dt_wtm_value = 0
dt_wtm_flag = 0
dt_wtm_user = 1
dt_wtm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
dt_user = "SILAHKAN LOGIN"
dt_no_antrian = ""
dt_no_reg = ""
dt_no_uji = ""
dt_nama = ""
dt_jenis_kendaraan = ""

class ScreenLogin(MDScreen):
    def __init__(self, **kwargs):
        super(ScreenLogin, self).__init__(**kwargs)

    def exec_cancel(self):
        try:
            self.ids.tx_username.text = ""
            self.ids.tx_password.text = ""    

        except Exception as e:
            toast_msg = f'error Login: {e}'

    def exec_login(self):
        global mydb, db_users
        global dt_wtm_user, dt_user

        try:
            input_username = self.ids.tx_username.text
            input_password = self.ids.tx_password.text       
            # Adding salt at the last of the password
            dataBase_password = input_password
            # Encoding the password
            hashed_password = hashlib.md5(dataBase_password.encode())

            mycursor = mydb.cursor()
            mycursor.execute("SELECT id_user, nama, username, password, nama FROM users WHERE username = '"+str(input_username)+"' and password = '"+str(hashed_password.hexdigest())+"'")
            myresult = mycursor.fetchone()
            db_users = np.array(myresult).T
            #if invalid
            if myresult == 0:
                toast('Gagal Masuk, Nama Pengguna atau Password Salah')
            #else, if valid
            else:
                toast_msg = f'Berhasil Masuk, Selamat Datang {myresult[1]}'
                toast(toast_msg)
                dt_wtm_user = myresult[0]
                dt_user = myresult[1]
                self.ids.tx_username.text = ""
                self.ids.tx_password.text = "" 
                self.screen_manager.current = 'screen_main'

        except Exception as e:
            toast_msg = f'error Login: {e}'
            toast(toast_msg)        
            toast('Gagal Masuk, Nama Pengguna atau Password Salah')

class ScreenMain(MDScreen):   
    dialog = None

    def __init__(self, **kwargs):
        super(ScreenMain, self).__init__(**kwargs)
        global mydb, db_antrian
        global audio, stream
        global flag_conn_stat, flag_play
        global count_starting, count_get_data, db_slm_value

        Clock.schedule_interval(self.regular_update_connection, 5)
        Clock.schedule_once(self.delayed_init, 1)

        flag_conn_stat = False
        flag_play = False
        count_starting = COUNT_STARTING
        count_get_data = COUNT_ACQUISITION
        self.reset_data()
        audio = pyaudio.PyAudio() # start the PyAudio class
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,
                            frames_per_buffer=CHUNK)

        try:
            mydb = mysql.connector.connect(
            host = DB_HOST,
            user = DB_USER,
            password = DB_PASSWORD,
            database = DB_NAME
            )

        except Exception as e:
            toast_msg = f'error initiate Database: {e}'
            toast(toast_msg)  

    def reset_data(self):
        global db_slm_value, count_starting, count_get_data, dt_slm_value        
        count_starting = COUNT_STARTING
        count_get_data = COUNT_ACQUISITION
        dt_slm_value = 0.0
        db_slm_value = np.array([0.0])

    def regular_update_connection(self, dt):
        global wtm_device
        global flag_conn_stat

        try:
            com_ports = list(ports.comports()) # create a list of com ['COM1','COM2'] 
            for i in com_ports:
                if i.name == COM_PORT_WTM:
                    flag_conn_stat = True

            wtm_device = serial.Serial()
            wtm_device.baudrate = 115200
            wtm_device.port = COM_PORT_WTM
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS        

            wtm_device = serial.Serial(devfile = COM_PORT_WTM,
                    baudrate = 115200,
                    bytesize = 8,
                    parity = 'N',
                    stopbits = 1,
                    timeout = 1.00)
            
            wtm_device.open()
            
        except Exception as e:
            toast_msg = f'error initiate WTM Device'
            toast(toast_msg)   
            flag_conn_stat = False

    def delayed_init(self, dt):
        Clock.schedule_interval(self.regular_update_display, 1)
        layout = self.ids.layout_table
        
        self.data_tables = MDDataTable(
            use_pagination=True,
            pagination_menu_pos="auto",
            rows_num=10,
            column_data=[
                ("No.", dp(10), self.sort_on_num),
                ("Antrian", dp(20)),
                ("No. Reg", dp(25)),
                ("No. Uji", dp(35)),
                ("Nama", dp(35)),
                ("Jenis", dp(50)),
                ("Status HLM", dp(20)),
                ("Status SLM", dp(20)),
                ("status WTM", dp(20))
            ],
        )
        self.data_tables.bind(on_row_press=self.on_row_press)
        layout.add_widget(self.data_tables)
        self.exec_reload_table()

    def sort_on_num(self, data):
        try:
            return zip(*sorted(enumerate(data),key=lambda l: l[0][0]))
        except:
            toast("Error sorting data")

    def on_row_press(self, table, row):
        global dt_no_antrian, dt_no_reg, dt_no_uji, dt_nama, dt_jenis_kendaraan
        global dt_wtm_flag, dt_wtm_value, dt_wtm_user, dt_wtm_post
        global dt_slm_flag, dt_slm_value, dt_slm_user, dt_slm_post
        global dt_hlm_flag, dt_hlm_user, dt_hlm_post

        try:
            start_index, end_index  = row.table.recycle_data[row.index]["range"]
            dt_no_antrian           = row.table.recycle_data[start_index + 1]["text"]
            dt_no_reg               = row.table.recycle_data[start_index + 2]["text"]
            dt_no_uji               = row.table.recycle_data[start_index + 3]["text"]
            dt_nama                 = row.table.recycle_data[start_index + 4]["text"]
            dt_jenis_kendaraan      = row.table.recycle_data[start_index + 5]["text"]
            dt_hlm_flag             = row.table.recycle_data[start_index + 6]["text"]
            dt_slm_flag             = row.table.recycle_data[start_index + 7]["text"]
            dt_wtm_flag             = row.table.recycle_data[start_index + 8]["text"]

        except Exception as e:
            toast_msg = f'error update table: {e}'
            toast(toast_msg)   

    def regular_update_display(self, dt):
        global flag_conn_stat
        global count_starting, count_get_data
        global dt_user, dt_no_antrian, dt_no_reg, dt_no_uji, dt_nama, dt_jenis_kendaraan
        global dt_hlm_flag, dt_hlm_value, dt_hlm_user, dt_hlm_post
        global dt_slm_flag, dt_slm_value, dt_slm_user, dt_slm_post
        global dt_wtm_flag, dt_wtm_value, dt_wtm_user, dt_wtm_post
        
        try:
            screen_login = self.screen_manager.get_screen('screen_login')
            screen_hlm = self.screen_manager.get_screen('screen_hlm')
            screen_slm = self.screen_manager.get_screen('screen_slm')
            screen_wtm = self.screen_manager.get_screen('screen_wtm')

            self.ids.lb_time.text = str(time.strftime("%H:%M:%S", time.localtime()))
            self.ids.lb_date.text = str(time.strftime("%d/%m/%Y", time.localtime()))
            screen_login.ids.lb_time.text = str(time.strftime("%H:%M:%S", time.localtime()))
            screen_login.ids.lb_date.text = str(time.strftime("%d/%m/%Y", time.localtime()))
            screen_hlm.ids.lb_time.text = str(time.strftime("%H:%M:%S", time.localtime()))
            screen_hlm.ids.lb_date.text = str(time.strftime("%d/%m/%Y", time.localtime()))
            screen_slm.ids.lb_time.text = str(time.strftime("%H:%M:%S", time.localtime()))
            screen_slm.ids.lb_date.text = str(time.strftime("%d/%m/%Y", time.localtime()))
            screen_wtm.ids.lb_time.text = str(time.strftime("%H:%M:%S", time.localtime()))
            screen_wtm.ids.lb_date.text = str(time.strftime("%d/%m/%Y", time.localtime()))
            
            self.ids.lb_no_antrian.text = str(dt_no_antrian)
            self.ids.lb_no_reg.text = str(dt_no_reg)
            self.ids.lb_no_uji.text = str(dt_no_uji)
            self.ids.lb_nama.text = str(dt_nama)
            self.ids.lb_jenis_kendaraan.text = str(dt_jenis_kendaraan)

            screen_hlm.ids.lb_no_antrian.text = str(dt_no_antrian)
            screen_hlm.ids.lb_no_reg.text = str(dt_no_reg)
            screen_hlm.ids.lb_no_uji.text = str(dt_no_uji)
            screen_hlm.ids.lb_nama.text = str(dt_nama)
            screen_hlm.ids.lb_jenis_kendaraan.text = str(dt_jenis_kendaraan)

            screen_slm.ids.lb_no_antrian.text = str(dt_no_antrian)
            screen_slm.ids.lb_no_reg.text = str(dt_no_reg)
            screen_slm.ids.lb_no_uji.text = str(dt_no_uji)
            screen_slm.ids.lb_nama.text = str(dt_nama)
            screen_slm.ids.lb_jenis_kendaraan.text = str(dt_jenis_kendaraan)

            screen_wtm.ids.lb_no_antrian.text = str(dt_no_antrian)
            screen_wtm.ids.lb_no_reg.text = str(dt_no_reg)
            screen_wtm.ids.lb_no_uji.text = str(dt_no_uji)
            screen_wtm.ids.lb_nama.text = str(dt_nama)
            screen_wtm.ids.lb_jenis_kendaraan.text = str(dt_jenis_kendaraan)

            if(dt_hlm_flag == "Belum Tes"):
                self.ids.bt_start_hlm.disabled = False
            else:
                self.ids.bt_start_hlm.disabled = True
            if(dt_slm_flag == "Belum Tes"):
                self.ids.bt_start_slm.disabled = False
            else:
                self.ids.bt_start_slm.disabled = True
            if(dt_wtm_flag == "Belum Tes"):
                self.ids.bt_start_wtm.disabled = False
            else:
                self.ids.bt_start_wtm.disabled = True

            if(not flag_play):
                screen_hlm.ids.bt_save.md_bg_color = colors['Green']['200']
                screen_hlm.ids.bt_save.disabled = False
                screen_hlm.ids.bt_reload.md_bg_color = colors['Red']['A200']
                screen_hlm.ids.bt_reload.disabled = False
                screen_slm.ids.bt_save.md_bg_color = colors['Green']['200']
                screen_slm.ids.bt_save.disabled = False
                screen_slm.ids.bt_reload.md_bg_color = colors['Red']['A200']
                screen_slm.ids.bt_reload.disabled = False
                screen_wtm.ids.bt_save.md_bg_color = colors['Green']['200']
                screen_wtm.ids.bt_save.disabled = False
                screen_wtm.ids.bt_reload.md_bg_color = colors['Red']['A200']
                screen_wtm.ids.bt_reload.disabled = False
            else:
                screen_hlm.ids.bt_reload.disabled = True
                screen_hlm.ids.bt_save.disabled = True
                screen_slm.ids.bt_reload.disabled = True
                screen_slm.ids.bt_save.disabled = True
                screen_wtm.ids.bt_reload.disabled = True
                screen_wtm.ids.bt_save.disabled = True

            if(not flag_conn_stat):
                self.ids.lb_comm.color = colors['Red']['A200']
                self.ids.lb_comm.text = 'Alat WTM Tidak Terhubung'
                screen_login.ids.lb_comm.color = colors['Red']['A200']
                screen_login.ids.lb_comm.text = 'Alat WTM Tidak Terhubung'
                screen_hlm.ids.lb_comm.color = colors['Red']['A200']
                screen_hlm.ids.lb_comm.text = 'Alat WTM Tidak Terhubung'                
                screen_slm.ids.lb_comm.color = colors['Red']['A200']
                screen_slm.ids.lb_comm.text = 'Alat WTM Tidak Terhubung'
                screen_wtm.ids.lb_comm.color = colors['Red']['A200']
                screen_wtm.ids.lb_comm.text = 'Alat WTM Tidak Terhubung'
            else:
                self.ids.lb_comm.color = colors['Blue']['200']
                self.ids.lb_comm.text = 'Alat WTM Terhubung'
                screen_login.ids.lb_comm.color = colors['Blue']['200']
                screen_login.ids.lb_comm.text = 'Alat WTM Terhubung'
                screen_hlm.ids.lb_comm.color = colors['Blue']['200']
                screen_hlm.ids.lb_comm.text = 'Alat WTM Terhubung'
                screen_slm.ids.lb_comm.color = colors['Blue']['200']
                screen_slm.ids.lb_comm.text = 'Alat WTM Terhubung'
                screen_wtm.ids.lb_comm.color = colors['Blue']['200']
                screen_wtm.ids.lb_comm.text = 'Alat WTM Terhubung'


            if(count_starting <= 0):
                screen_hlm.ids.lb_test_subtitle.text = "HASIL PENGUKURAN"
                screen_hlm.ids.lb_hlm.text = str(np.round(dt_hlm_value, 2))
                screen_slm.ids.lb_test_subtitle.text = "HASIL PENGUKURAN"
                screen_slm.ids.lb_sound.text = str(np.round(dt_slm_value, 2))
                screen_wtm.ids.lb_test_subtitle.text = "HASIL PENGUKURAN"
                screen_wtm.ids.lb_window_tint.text = str(np.round(dt_wtm_value, 2))
                
                if(dt_hlm_value >= STANDARD_MIN_HLM):
                    screen_hlm.ids.lb_info.text = f"Ambang Batas intensitas cahaya adalah {STANDARD_MIN_HLM} lumen.\nLampu Depan Anda Memiliki Tingkat Intensitas Cahaya Dalam Range Ambang Batas"
                else:
                    screen_hlm.ids.lb_info.text = f"Ambang Batas intensitas cahaya adalah {STANDARD_MIN_HLM} lumen.\nLampu Depan Anda Memiliki Tingkat Intensitas Cahaya Diluar Ambang Batas"
                if(dt_slm_value >= STANDARD_MIN_SLM and dt_slm_value <= STANDARD_MAX_SLM):
                    screen_slm.ids.lb_info.text = f"Ambang Batas Kebisingan adalah {STANDARD_MIN_SLM} dB hingga {STANDARD_MAX_SLM} dB.\nKendaraan Anda Memiliki Tingkat Kebisingan Suara Klakson Dalam Range Ambang Batas"
                elif(dt_slm_value < STANDARD_MIN_SLM):
                    screen_slm.ids.lb_info.text = f"Ambang Batas Kebisingan adalah {STANDARD_MIN_SLM} dB hingga {STANDARD_MAX_SLM} dB.\nKendaraan Anda Memiliki Tingkat Kebisingan Suara Klakson Dibawah Ambang Batas"
                elif(dt_slm_value > STANDARD_MAX_SLM):
                    screen_slm.ids.lb_info.text = f"Ambang Batas Kebisingan adalah {STANDARD_MIN_SLM} dB hingga {STANDARD_MAX_SLM} dB.\nKendaraan Anda Memiliki Tingkat Kebisingan Suara Klakson Diatas Ambang Batas"
                if(dt_wtm_value >= STANDARD_MIN_WTM):
                    screen_wtm.ids.lb_info.text = f"Ambang Batas Tingkat Meneruskan Cahaya pada Kaca Kendaraan adalah {STANDARD_MIN_WTM} %.\nKaca Kendaraan Anda Memiliki Tingkat Meneruskan Cahaya Dalam Range Ambang Batas"
                else:
                    screen_wtm.ids.lb_info.text = f"Ambang Batas Tingkat Meneruskan Cahaya pada Kaca Kendaraan adalah {STANDARD_MIN_WTM} %.\nKaca Kendaraan Anda Memiliki Tingkat Meneruskan Cahaya Diluar Ambang Batas"
                                                                
            elif(count_starting > 0):
                if(flag_play):
                    screen_hlm.ids.lb_test_subtitle.text = "MEMULAI PENGUKURAN"
                    screen_hlm.ids.lb_hlm.text = str(count_starting)
                    screen_hlm.ids.lb_info.text = "Silahkan Nyalakan Lampu Depan"
                    screen_slm.ids.lb_test_subtitle.text = "MEMULAI PENGUKURAN"
                    screen_slm.ids.lb_sound.text = str(count_starting)
                    screen_slm.ids.lb_info.text = "Silahkan Nyalakan Klakson Kendaraan"                    
                    screen_wtm.ids.lb_test_subtitle.text = "MEMULAI PENGUKURAN"
                    screen_wtm.ids.lb_window_tint.text = str(count_starting)
                    screen_wtm.ids.lb_info.text = "Silahkan Tekan Tombol Pengukuran Alat WTM"

            if(count_get_data <= 0):
                if(not flag_play):
                    if(dt_hlm_value >= STANDARD_MIN_HLM):
                        screen_hlm.ids.lb_test_result.md_bg_color = colors['Green']['200']
                        screen_hlm.ids.lb_test_result.text = "LULUS"
                        dt_hlm_flag = "Lulus"
                        screen_hlm.ids.lb_test_result.text_color = colors['Green']['700']
                    else:
                        screen_hlm.ids.lb_test_result.md_bg_color = colors['Red']['A200']
                        screen_hlm.ids.lb_test_result.text = "TIDAK LULUS"
                        dt_hlm_flag = "Tidak Lulus"
                        screen_hlm.ids.lb_test_result.text_color = colors['Red']['A700']

                    if(dt_slm_value >= STANDARD_MIN_SLM and dt_slm_value <= STANDARD_MAX_SLM):
                        screen_slm.ids.lb_test_result.md_bg_color = colors['Green']['200']
                        screen_slm.ids.lb_test_result.text = "LULUS"
                        dt_slm_flag = "Lulus"
                        screen_slm.ids.lb_test_result.text_color = colors['Green']['700']
                    else:
                        screen_slm.ids.lb_test_result.md_bg_color = colors['Red']['A200']
                        screen_slm.ids.lb_test_result.text = "TIDAK LULUS"
                        dt_slm_flag = "Tidak Lulus"
                        screen_slm.ids.lb_test_result.text_color = colors['Red']['A700']   

                    if(dt_wtm_value >= STANDARD_MIN_WTM):
                        screen_wtm.ids.lb_test_result.md_bg_color = colors['Green']['200']
                        screen_wtm.ids.lb_test_result.text = "LULUS"
                        dt_wtm_flag = "Lulus"
                        screen_wtm.ids.lb_test_result.text_color = colors['Green']['700']
                    else:
                        screen_wtm.ids.lb_test_result.md_bg_color = colors['Red']['A200']
                        screen_wtm.ids.lb_test_result.text = "TIDAK LULUS"
                        dt_wtm_flag = "Tidak Lulus"
                        screen_wtm.ids.lb_test_result.text_color = colors['Red']['A700']


            elif(count_get_data > 0):
                    screen_hlm.ids.lb_test_result.md_bg_color = colors['Gray']['500']
                    screen_hlm.ids.lb_test_result.text = ""
                    screen_slm.ids.lb_test_result.md_bg_color = colors['Gray']['500']
                    screen_slm.ids.lb_test_result.text = ""                    
                    screen_wtm.ids.lb_test_result.md_bg_color = "#EEEEEE"
                    screen_wtm.ids.lb_test_result.text = ""

            self.ids.lb_operator.text = dt_user
            screen_login.ids.lb_operator.text = dt_user
            screen_hlm.ids.lb_operator.text = dt_user
            screen_slm.ids.lb_operator.text = dt_user            
            screen_wtm.ids.lb_operator.text = dt_user

        except Exception as e:
            toast_msg = f'error update display: {e}'
            toast(toast_msg)                

    def regular_get_data_hlm(self, dt):
        global flag_play
        global dt_hlm_value
        global count_starting, count_get_data
        try:
            if flag_play:
                if(count_starting > 0):
                    count_starting -= 1
                if(count_get_data > 0):
                    count_get_data -= 1
                elif(count_get_data <= 0):
                    flag_play = False
                    Clock.unschedule(self.regular_get_data_hlm)
                mycursor = mydb.cursor()
                mycursor.execute(f"SELECT hlm_value FROM {TB_MEASURE_HLM}")
                dt_hlm_value, = mycursor.fetchone()
                mydb.commit()

        except Exception as e:
            toast_msg = f'error get data: {e}'
            print(toast_msg) 

    def regular_get_data_slm(self, dt):
        global flag_play
        global dt_slm_value
        global db_slm_value, count_starting, count_get_data
        try:
            if flag_play:
                if(count_starting > 0):
                    count_starting -= 1
                if(count_get_data > 0):
                    count_get_data -= 1
                elif(count_get_data <= 0):
                    flag_play = False
                    Clock.unschedule(self.regular_get_data_slm)
                for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                    sound_rms = audioop.rms(stream.read(CHUNK), WIDTH) / 32767
                    # db = 20 * log10(sound_rms) #0.033, 0.109, 0.347
                    # mod = 20 * log10(rms * 32767)
                    amplitude = sound_rms * 1600000
                    # mod_Amp = amp * 1518727
                    if amplitude > 0:
                        dB = 20 * log10(amplitude)
                        dBA = dB if sound_rms > 0.03 else dB - (((0.3 - sound_rms) * 15 ) ** 2 )
                        # mod_dB = 20 * log10(sound_rms) + 93.37
                        # print(f"RMS: {sound_rms} DB: {db} mod_Amp: {mod_Amp} mod_dB: {mod_dB}")
                        db_slm_value = np.append(db_slm_value, dBA)
                        dt_slm_value = np.max(db_slm_value)
        except Exception as e:
            toast_msg = f'error get data: {e}'
            print(toast_msg) 

    def regular_get_data_wtm(self, dt):
        global flag_play
        global dt_wtm_value
        global count_starting, count_get_data
        global wtm_device
        try:
            if flag_play:
                if(count_starting > 0):
                    count_starting -= 1              
                if(count_get_data > 0):
                    count_get_data -= 1
                elif(count_get_data <= 0):
                    # flag_play = False
                    # Clock.unschedule(self.regular_get_data)
                # if(count_starting <= 0):
                    arr_ref = np.loadtxt("data\sample_data.csv", delimiter=";", dtype=str, skiprows=1)
                    arr_val_ref = arr_ref[:,0]
                    arr_data_ref = arr_ref[:,1:]
                    data_byte = wtm_device.readline().decode("utf-8").strip()  # read the incoming data and remove newline character
                    if data_byte != "":
                        arr_data_byte = np.array(data_byte.split())
                        for i in range(arr_val_ref.size):
                            if(np.array_equal(arr_data_byte, arr_data_ref[i])):
                                dt_wtm_value = float(arr_val_ref[i])
                    flag_play = False
                    Clock.unschedule(self.regular_get_data_wtm)
        except Exception as e:
            toast_msg = f'error get data: {e}'
            print(toast_msg) 


    def exec_reload_table(self):
        global mydb, db_antrian
        try:
            mycursor = mydb.cursor()
            mycursor.execute(f"SELECT noantrian, nopol, nouji, user, idjeniskendaraan, hlm_flag, slm_flag, wtm_flag FROM {TB_DATA}")
            myresult = mycursor.fetchall()
            mydb.commit()
            db_antrian = np.array(myresult).T

            self.data_tables.row_data=[(f"{i+1}", f"{db_antrian[0, i]}", f"{db_antrian[1, i]}", f"{db_antrian[2, i]}", f"{db_antrian[3, i]}" ,f"{db_antrian[4, i]}", 
                                        'Belum Tes' if (int(db_antrian[5, i]) == 0) else ('Lulus' if (int(db_antrian[5, i]) == 1) else 'Tidak Lulus'),
                                        'Belum Tes' if (int(db_antrian[6, i]) == 0) else ('Lulus' if (int(db_antrian[6, i]) == 1) else 'Tidak Lulus'), 
                                        'Belum Tes' if (int(db_antrian[7, i]) == 0) else ('Lulus' if (int(db_antrian[7, i]) == 1) else 'Tidak Lulus')) 
                                        for i in range(len(db_antrian[0]))]

        except Exception as e:
            toast_msg = f'error reload table: {e}'
            print(toast_msg)

    def exec_start_hlm(self):
        global flag_play, stream, audio

        if(not flag_play):
            Clock.schedule_interval(self.regular_get_data_hlm, 1)
            self.open_screen_hlm()
            flag_play = True

    def exec_start_slm(self):
        global flag_play, stream, audio

        if(not flag_play):
            stream.start_stream()
            Clock.schedule_interval(self.regular_get_data_slm, 1)
            self.open_screen_slm()
            flag_play = True

    def exec_start_wtm(self):
        global flag_play, stream, audio
        if(not flag_play):
            # stream.start_stream()
            Clock.schedule_interval(self.regular_get_data_wtm, 1)
            self.open_screen_wtm()
            flag_play = True

    def open_screen_hlm(self):
        self.screen_manager.current = 'screen_hlm'

    def open_screen_wtm(self):
        self.screen_manager.current = 'screen_wtm'

    def open_screen_slm(self):
        self.screen_manager.current = 'screen_slm'

    def exec_logout(self):
        self.screen_manager.current = 'screen_login'

class ScreenHLM(MDScreen):        
    def __init__(self, **kwargs):
        super(ScreenHLM, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init, 2)
        
    def delayed_init(self, dt):
        pass

    def reset_data(self):
        global count_starting, count_get_data, dt_hlm_value

        count_starting = COUNT_STARTING
        count_get_data = COUNT_ACQUISITION
        dt_hlm_value = 0.0

    def exec_start(self):
        global flag_play
        screen_main = self.screen_manager.get_screen('screen_main')
        self.reset_data()
        if(not flag_play):
            Clock.schedule_interval(screen_main.regular_get_data_hlm, 1)
            flag_play = True

    def exec_reload(self):
        global flag_play

        screen_main = self.screen_manager.get_screen('screen_main')
        self.reset_data()
        self.ids.bt_reload.disabled = True

        if(not flag_play):
            Clock.schedule_interval(screen_main.regular_get_data_hlm, 1)
            flag_play = True

    def exec_save(self):
        global flag_play
        global count_starting, count_get_data
        global mydb, db_antrian
        global dt_no_antrian, dt_no_reg, dt_no_uji, dt_nama, dt_jenis_kendaraan
        global dt_hlm_flag, dt_hlm_value, dt_hlm_user, dt_hlm_post

        try:
            self.ids.bt_save.disabled = True

            mycursor = mydb.cursor()
            sql = f"UPDATE {TB_DATA} SET hlm_flag = %s, hlm_value = %s, hlm_user = %s, hlm_post = %s WHERE noantrian = %s"
            sql_hlm_flag = (1 if dt_hlm_flag == "Lulus" else 2)
            dt_hlm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
            print_datetime = str(time.strftime("%d %B %Y %H:%M:%S", time.localtime()))
            sql_val = (sql_hlm_flag, dt_hlm_value, dt_hlm_user, dt_hlm_post, dt_no_antrian)
            mycursor.execute(sql, sql_val)
            mydb.commit()
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
        
class ScreenSLM(MDScreen):        
    def __init__(self, **kwargs):
        super(ScreenSLM, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init, 2)
        
    def delayed_init(self, dt):
        pass

    def reset_data(self):
        global db_slm_value, count_starting, count_get_data, dt_slm_value

        count_starting = COUNT_STARTING
        count_get_data = COUNT_ACQUISITION
        dt_slm_value = 0.0
        db_slm_value = np.array([0.0])

    def exec_start(self):
        global flag_play

        screen_main = self.screen_manager.get_screen('screen_main')
        self.reset_data()

        if(not flag_play):
            stream.start_stream()
            Clock.schedule_interval(screen_main.regular_get_data_slm, 1)
            flag_play = True

    def exec_reload(self):
        global flag_play

        screen_main = self.screen_manager.get_screen('screen_main')
        self.reset_data()
        self.ids.bt_reload.disabled = True

        if(not flag_play):
            stream.start_stream()
            Clock.schedule_interval(screen_main.regular_get_data_slm, 1)
            flag_play = True

    def exec_save(self):
        global flag_play
        global count_starting, count_get_data
        global mydb, db_antrian
        global dt_no_antrian, dt_no_reg, dt_no_uji, dt_nama, dt_jenis_kendaraan
        global dt_slm_flag, dt_slm_value, dt_slm_user, dt_slm_post

        try:
            self.ids.bt_save.disabled = True

            mycursor = mydb.cursor()

            sql = f"UPDATE {TB_DATA} SET slm_flag = %s, slm_value = %s, slm_user = %s, slm_post = %s WHERE noantrian = %s"
            sql_slm_flag = (1 if dt_slm_flag == "Lulus" else 2)
            dt_slm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
            print_datetime = str(time.strftime("%d %B %Y %H:%M:%S", time.localtime()))
            sql_val = (sql_slm_flag, float(dt_slm_value), dt_slm_user, dt_slm_post, dt_no_antrian)
            mycursor.execute(sql, sql_val)
            mydb.commit()
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

class ScreenWTM(MDScreen):        
    def __init__(self, **kwargs):
        super(ScreenWTM, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init, 2)
        #
    def delayed_init(self, dt):
        pass

    def exec_start(self):
        global flag_play
        global count_starting, count_get_data

        screen_main = self.screen_manager.get_screen('screen_main')

        count_starting = COUNT_STARTING
        count_get_data = COUNT_ACQUISITION

        if(not flag_play):
            stream.start_stream()
            Clock.schedule_interval(screen_main.regular_get_data_wtm, 1)
            flag_play = True

    def exec_reload(self):
        global flag_play
        global count_starting, count_get_data, dt_wtm_value

        screen_main = self.screen_manager.get_screen('screen_main')

        count_starting = COUNT_STARTING
        count_get_data = COUNT_ACQUISITION
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

        try:
            self.ids.bt_save.disabled = True

            mycursor = mydb.cursor()

            sql = f"UPDATE {TB_DATA} SET wtm_flag = %s, wtm_value = %s, wtm_user = %s, wtm_post = %s WHERE noantrian = %s"
            sql_wtm_flag = (1 if dt_wtm_flag == "Lulus" else 2)
            dt_wtm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
            print_datetime = str(time.strftime("%d %B %Y %H:%M:%S", time.localtime()))
            sql_val = (sql_wtm_flag, dt_wtm_value, dt_wtm_user, dt_wtm_post, dt_no_antrian)
            mycursor.execute(sql, sql_val)
            mydb.commit()
            self.open_screen_main()
        
        except Exception as e:
            toast_msg = f'error Save Data: {e}'
            toast(toast_msg) 

    def open_screen_main(self):
        global flag_play        
        global count_starting, count_get_data

        screen_main = self.screen_manager.get_screen('screen_main')

        count_starting = COUNT_STARTING
        count_get_data = COUNT_ACQUISITION
        flag_play = False   
        screen_main.exec_reload_table()
        Clock.unschedule(screen_main.regular_get_data_wtm)
        self.screen_manager.current = 'screen_main'

    def exec_logout(self):
        self.screen_manager.current = 'screen_login'

class RootScreen(ScreenManager):
    pass             

class HeadSoundWindowMeterApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self):
        self.theme_cls.colors = colors
        self.theme_cls.primary_palette = "Gray"
        self.theme_cls.accent_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.icon = 'assets/logo.png'

        LabelBase.register(
            name="Orbitron-Regular",
            fn_regular="assets/fonts/Orbitron-Regular.ttf")

        theme_font_styles.append('Display')
        self.theme_cls.font_styles["Display"] = [
            "Orbitron-Regular", 72, False, 0.15]       
        
        Window.fullscreen = 'auto'
        # Window.borderless = False
        # Window.size = 900, 1440
        # Window.size = 450, 720
        # Window.allow_screensaver = True

        Builder.load_file('main.kv')
        return RootScreen()

if __name__ == '__main__':
    HeadSoundWindowMeterApp().run()
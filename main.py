from attr import s
import serial
from serial.tools import list_ports
import cv2

import os, sys, time
import ssl
import datetime
from kivy.graphics.texture import Texture
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    running_mode = 'Frozen/executable'
else:
    try:
        app_full_path = os.path.realpath(__file__)
        application_path = os.path.dirname(app_full_path)
        running_mode = "Non-interactive"
    except NameError:
        application_path = os.getcwd()
        running_mode = 'Interactive'

logger_name = f'app.log'
logger_dir = os.path.join(application_path, "logs")

from kivy.config import Config
Config.set('kivy', 'keyboard_mode', 'system')

from kivy.logger import Logger
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager
from kivymd.font_definitions import theme_font_styles
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.textfield import MDTextField
from kivy.metrics import dp
from kivymd.toast import toast
from kivymd.app import MDApp
import numpy as np
import configparser, hashlib, mysql.connector
from pymodbus.client import ModbusTcpClient
from fpdf import FPDF
from kivy.resources import resource_add_path
from kivymd.uix.datatables import MDDataTable
import pyaudio, audioop
from math import log10
import serial.tools.list_ports as ports, serial



colors = {
    "Red"   : {"A200": "#FF2A2A","A500": "#FF8080","A700": "#FFD5D5",},
    "Gray"  : {"200": "#CCCCCC","500": "#ECECEC","700": "#F9F9F9",},
    "Blue"  : {"200": "#4471C4","500": "#5885D8","700": "#6C99EC",},
    "Green" : {"200": "#2CA02C","500": "#2DB97F", "700": "#D5FFD5",},
    "Yellow": {"200": "#ffD42A","500": "#ffE680","700": "#fff6D5",},

    "Light" : {"StatusBar": "E0E0E0","AppBar": "#202020","Background": "#EEEEEE","CardsDialogs": "#FFFFFF","FlatButtonDown": "#CCCCCC",},
    "Dark"  : {"StatusBar": "101010","AppBar": "#E0E0E0","Background": "#111111","CardsDialogs": "#222222","FlatButtonDown": "#DDDDDD",},
}

# --- MODEL KALIBRASI SOUND LEVEL METER ---
calibration_data = np.array([
    [0.2400, 52.0],
    [0.3055, 60.3],
    [0.3789, 65.5],
    [0.4888, 74.6],
    [0.6276, 84.7],
    [0.7417, 94.3],
    [0.9718, 105.0]
])

amplitudo_samples = calibration_data[:, 0]
db_samples = calibration_data[:, 1]
coefficients = np.polyfit(amplitudo_samples, db_samples, 2)
db_conversion_model = np.poly1d(coefficients)

def konversi_ke_db(amplitudo_rms):
    if amplitudo_rms < 0.001:
        return 0.0  
    db_value = db_conversion_model(amplitudo_rms)
    return db_value
#-------------------------------------------------------

config_name = 'config.ini'
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    running_mode = 'Frozen/executable'
else:
    try:
        app_full_path = os.path.realpath(__file__)
        application_path = os.path.dirname(app_full_path)
        running_mode = "Non-interactive (e.g. 'python myapp.py')"
    except NameError:
        application_path = os.getcwd()
        running_mode = 'Interactive'

config_full_path = os.path.join(application_path, config_name)
config = configparser.ConfigParser()
config.read(config_full_path)

## App Setting
APP_TITLE = config['app']['APP_TITLE']
APP_SUBTITLE = config['app']['APP_SUBTITLE']
IMG_LOGO_PEMKAB = config['app']['IMG_LOGO_PEMKAB']
IMG_LOGO_DISHUB = config['app']['IMG_LOGO_DISHUB']
LB_PEMKAB = config['app']['LB_PEMKAB']
LB_DISHUB = config['app']['LB_DISHUB']
LB_UNIT = config['app']['LB_UNIT']
LB_UNIT_ADDRESS = config['app']['LB_UNIT_ADDRESS']

# SQL setting
# DB_HOST = "194.31.53.37"
# DB_USER = "Pndujikir2022!"
# DB_PASSWORD = "@Kirpnd2022!"
# DB_NAME = "pkbpandeglang"
DB_HOST = "156.67.217.60"
DB_USER = "pkbsorong2024!"
DB_PASSWORD = "@Sorongpkb2024"
DB_NAME = "dishub"
TB_DATA = "tb_cekident"
TB_USER = "users"
TB_MERK = "merk"
TB_BAHAN_BAKAR = "bahanbakar"
TB_WARNA = "warna"
TB_DATA_MASTER = "identkendaraan"

FTP_HOST = "194.31.53.37"
FTP_USER = "root"
FTP_PASS = "@D15HUBp2022!"

# system setting
TIME_OUT = int(config['setting']['TIME_OUT'])
COUNT_STARTING = int(config['setting']['COUNT_STARTING'])
COUNT_ACQUISITION = int(config['setting']['COUNT_ACQUISITION'])
UPDATE_CAROUSEL_INTERVAL = float(config['setting']['UPDATE_CAROUSEL_INTERVAL'])
UPDATE_CONNECTION_INTERVAL = float(config['setting']['UPDATE_CONNECTION_INTERVAL'])
GET_DATA_INTERVAL = float(config['setting']['GET_DATA_INTERVAL'])

COM_PORT_WTM = config['setting']['COM_PORT_WTM']

# system standard
STANDARD_MIN_HLM_LEFT = float(config['standard']['STANDARD_MIN_HLM_LEFT']) # in cd / candela
STANDARD_MIN_HLM_RIGHT = float(config['standard']['STANDARD_MIN_HLM_RIGHT']) # in cd / candela
STANDARD_MAX_ANGLE_DIFF_HLM_LEFT = float(config['standard']['STANDARD_MAX_ANGLE_DIFF_HLM_LEFT']) # in degree
STANDARD_MAX_ANGLE_DIFF_HLM_RIGHT = float(config['standard']['STANDARD_MAX_ANGLE_DIFF_HLM_RIGHT']) # in degree
STANDARD_MIN_SLM = float(config['standard']['STANDARD_MIN_SLM']) # in dbm
STANDARD_MAX_SLM = float(config['standard']['STANDARD_MAX_SLM']) # in dbm
STANDARD_MIN_WTM = float(config['standard']['STANDARD_MIN_WTM']) # in %

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 0.8
WIDTH = 2

db_slm_value = np.array([0.0])
dt_slm_value = 0
dt_slm_flag = 0
dt_slm_user = 1
dt_slm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
dt_hlm_left_value = 0
dt_hlm_right_value = 0
dt_hlm_diff_left_value = 0
dt_hlm_diff_right_value = 0
dt_hlm_flag = 0
dt_hlm_user = 1
dt_slm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
dt_wtm_value = 0
dt_wtm_flag = 0
dt_wtm_user = 1
dt_wtm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
dt_user = ""
dt_no_antrian = ""
dt_no_pol = ""
dt_no_uji = ""
dt_nama = ""
dt_jenis_kendaraan = ""

dt_dash_pendaftaran = 0
dt_dash_belum_uji = 0
dt_dash_sudah_uji = 0
wtm_device = None 
wtm_arr_val_ref = None
wtm_arr_data_ref = None

try:
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
except Exception as e:
    toast_msg = f'Error Stream audio: {e}'
    print(toast_msg)    

class ScreenHome(MDScreen):
    def __init__(self, **kwargs):
        super(ScreenHome, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init, 1)

    def delayed_init(self, dt):
        self.ids.lb_title.text = APP_TITLE
        self.ids.lb_subtitle.text = APP_SUBTITLE        
        self.ids.img_pemkab.source = f'assets/images/{IMG_LOGO_PEMKAB}'
        self.ids.img_dishub.source = f'assets/images/{IMG_LOGO_DISHUB}'
        self.ids.lb_pemkab.text = LB_PEMKAB
        self.ids.lb_dishub.text = LB_DISHUB
        self.ids.lb_unit.text = LB_UNIT
        self.ids.lb_unit_address.text = LB_UNIT_ADDRESS
        Clock.schedule_interval(self.regular_update_carousel, UPDATE_CAROUSEL_INTERVAL)

    def regular_update_carousel(self, dt):
        try:
            self.ids.carousel.index += 1
            
        except Exception as e:
            toast_msg = f'Gagal Memperbaharui Tampilan Carousel'
            toast_msg = f'Error Update Carousel: {e}'
            toast(toast_msg)               

    def exec_navigate_home(self):
        try:
            self.screen_manager.current = 'screen_home'

        except Exception as e:
            toast_msg = f'Error Navigate to Home Screen: {e}'
            toast(toast_msg)        

    def exec_navigate_login(self):
        global dt_user
        try:
            if (dt_user == ""):
                self.screen_manager.current = 'screen_login'
            else:
                toast(f"Anda sudah login sebagai {dt_user}")

        except Exception as e:
            toast_msg = f'Terjadi kesalahan saat berpindah ke halaman Login'
            toast(toast_msg)
            Logger.error(f"{self.name}: {toast_msg}, {e}")       

    def exec_navigate_main(self):
        try:
            self.screen_manager.current = 'screen_main'

        except Exception as e:
            toast_msg = f'Terjadi kesalahan saat berpindah ke halaman Utama'
            toast(toast_msg)
            Logger.error(f"{self.name}: {toast_msg}, {e}")  

class ScreenLogin(MDScreen):
    def __init__(self, **kwargs):
        super(ScreenLogin, self).__init__(**kwargs)
    
    def delayed_init(self, dt):
        self.ids.lb_title.text = APP_TITLE
        self.ids.lb_subtitle.text = APP_SUBTITLE  
        self.ids.img_pemkab.source = f'assets/images/{IMG_LOGO_PEMKAB}'
        self.ids.img_dishub.source = f'assets/images/{IMG_LOGO_DISHUB}'
        self.ids.lb_pemkab.text = LB_PEMKAB
        self.ids.lb_dishub.text = LB_DISHUB
        self.ids.lb_unit.text = LB_UNIT
        self.ids.lb_unit_address.text = LB_UNIT_ADDRESS

    def exec_cancel(self):
        try:
            self.ids.tx_username.text = ""
            self.ids.tx_password.text = ""    

        except Exception as e:
            toast_msg = f'error Login: {e}'

    def exec_login(self):
        global mydb
        global dt_id_user, dt_user, dt_slm_user, dt_hlm_user, dt_wtm_user

        screen_main = self.screen_manager.get_screen('screen_main')

        try:
            screen_main.exec_reload_database()
            input_username = self.ids.tx_username.text
            input_password = self.ids.tx_password.text
            dataBase_password = input_password
            hashed_password = hashlib.md5(dataBase_password.encode())
            mycursor = mydb.cursor(buffered=True)
            mycursor.execute(f"SELECT id_user, nama, username, password, nama FROM {TB_USER} WHERE username = '{input_username}' and password = '{hashed_password.hexdigest()}'")
            myresult = mycursor.fetchone()
            
            if myresult is None:
                toast_msg = f'Gagal Masuk, Nama Pengguna atau Password Salah'
                toast(toast_msg) 
                Logger.warning(f"{self.name}: {toast_msg}") 
            else:
                toast_msg = f'Berhasil Masuk, Selamat Datang {myresult[1]}'
                toast(toast_msg)
                Logger.info(f"{self.name}: {toast_msg}")  
                dt_id_user = myresult[0]
                dt_user = myresult[1]
                
                # PERBAIKAN UTAMA DI SINI
                dt_hlm_user = dt_id_user
                dt_slm_user = dt_id_user
                dt_wtm_user = dt_id_user
                
                self.ids.tx_username.text = ""
                self.ids.tx_password.text = "" 
                self.screen_manager.current = 'screen_main'

        except Exception as e:
            toast_msg = f'Error Login: {e}'
            toast(toast_msg)      
            toast('Gagal Masuk, Nama Pengguna atau Password Salah')

        except Exception as e:
            toast_msg = f'error Login: {e}'
            toast(toast_msg)      
            toast('Gagal Masuk, Nama Pengguna atau Password Salah')

        except Exception as e:
            toast_msg = f'error Login: {e}'
            toast(toast_msg)        
            toast('Gagal Masuk, Nama Pengguna atau Password Salah')

    def exec_navigate_home(self):
        try:
            self.screen_manager.current = 'screen_home'

        except Exception as e:
            toast_msg = f'Gagal Berpindah ke Halaman Awal'
            toast(toast_msg)
            Logger.error(f"{self.name}: {toast_msg}, {e}")      

    def exec_navigate_login(self):
        global dt_user
        try:
            if (dt_user == ""):
                self.screen_manager.current = 'screen_login'
            else:
                toast_msg = f"Anda sudah login sebagai {dt_user}"
                toast(toast_msg)
                Logger.info(f"{self.name}: {toast_msg}")  

        except Exception as e:
            toast_msg = f'Gagal Berpindah ke Halaman Login'
            toast(toast_msg)
            Logger.error(f"{self.name}: {toast_msg}, {e}")    

    def exec_navigate_main(self):
        try:
            self.screen_manager.current = 'screen_main'

        except Exception as e:
            toast_msg = f'Gagal Berpindah ke Halaman Utama'
            toast(toast_msg)
            Logger.error(f"{self.name}: {toast_msg}, {e}") 

class ScreenMain(MDScreen):   
    def __init__(self, **kwargs):
        super(ScreenMain, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init, 1)                 

    def delayed_init(self, dt):
        global flag_conn_stat, flag_play
        global count_starting, count_get_data

        flag_conn_stat = False
        flag_play = False

        self.ids.lb_title.text = APP_TITLE
        self.ids.lb_subtitle.text = APP_SUBTITLE              
        self.ids.img_pemkab.source = f'assets/images/{IMG_LOGO_PEMKAB}'
        self.ids.img_dishub.source = f'assets/images/{IMG_LOGO_DISHUB}'
        self.ids.lb_pemkab.text = LB_PEMKAB
        self.ids.lb_dishub.text = LB_DISHUB
        self.ids.lb_unit.text = LB_UNIT
        self.ids.lb_unit_address.text = LB_UNIT_ADDRESS

        count_starting = COUNT_STARTING
        count_get_data = COUNT_ACQUISITION
        
        Clock.schedule_interval(self.regular_update_display, 1)
        Clock.schedule_interval(self.regular_update_connection, UPDATE_CONNECTION_INTERVAL)
        self.load_wtm_reference_data()
        self.exec_reload_database()
        self.exec_reload_table()

    def on_antrian_row_press(self, instance):
            global dt_no_antrian, dt_no_pol, dt_no_uji, dt_nama, dt_hlm_flag, dt_slm_flag, dt_wtm_flag
            global dt_merk, dt_type, dt_jenis_kendaraan, dt_jbb, dt_bahan_bakar, dt_warna
            global db_antrian, db_merk

            try:
                row = int(str(instance.id).replace("card_antrian",""))
                dt_no_antrian          = f"{db_antrian[0, row]}"
                dt_no_pol              = f"{db_antrian[1, row]}"
                dt_no_uji              = f"{db_antrian[2, row]}"
                # PENTING: Ubah flag menjadi teks yang lebih deskriptif untuk ditampilkan di menu
                dt_hlm_flag            = 'Lulus' if (int(db_antrian[3, row]) == 1) else 'Tidak Lulus' if (int(db_antrian[3, row]) == 0) else 'Belum Uji'
                dt_slm_flag            = 'Lulus' if (int(db_antrian[4, row]) == 1) else 'Tidak Lulus' if (int(db_antrian[4, row]) == 0) else 'Belum Uji'
                dt_wtm_flag            = 'Lulus' if (int(db_antrian[5, row]) == 1) else 'Tidak Lulus' if (int(db_antrian[5, row]) == 0) else 'Belum Uji'
                dt_nama                = f"{db_antrian[6, row]}"
                dt_merk                = f"{db_merk[np.where(db_merk == db_antrian[7, row])[0][0],1]}"
                dt_type                = f"{db_antrian[8, row]}"
                dt_jenis_kendaraan     = f"{db_antrian[9, row]}"
                dt_jbb                 = f"{db_antrian[10, row]}"
                dt_bahan_bakar         = f"{db_antrian[11, row]}"
                dt_warna               = f"{db_antrian[12, row]}"
                
                # Ganti pemanggilan exec_start() dengan navigasi ke menu
                self.manager.current = 'screen_menu' # <-- INI PERUBAHANNYA

            except Exception as e:
                toast_msg = f'Error Execute Command from Table Row: {e}'
                toast(toast_msg)

    def regular_update_display(self, dt):
        global flag_conn_stat
        global count_starting, count_get_data
        global dt_user, dt_no_antrian, dt_no_pol, dt_no_uji, dt_nama, dt_jenis_kendaraan
        global dt_hlm_flag, dt_hlm_left_value, dt_hlm_right_value, dt_hlm_diff_left_value, dt_hlm_diff_right_value, dt_hlm_user, dt_hlm_post
        global dt_slm_flag, dt_slm_value, dt_slm_user, dt_slm_post
        global dt_wtm_flag, dt_wtm_value, dt_wtm_user, dt_wtm_post
        
        try:
            screen_home = self.screen_manager.get_screen('screen_home')
            screen_login = self.screen_manager.get_screen('screen_login')
            screen_menu = self.screen_manager.get_screen('screen_menu')
            screen_hlm = self.screen_manager.get_screen('screen_hlm')
            screen_slm = self.screen_manager.get_screen('screen_slm')
            screen_wtm = self.screen_manager.get_screen('screen_wtm')
            screen_calibration = self.screen_manager.get_screen('screen_calibration')

            self.ids.lb_time.text = str(time.strftime("%H:%M:%S", time.localtime()))
            self.ids.lb_date.text = str(time.strftime("%d/%m/%Y", time.localtime()))
            screen_home.ids.lb_time.text = str(time.strftime("%H:%M:%S", time.localtime()))
            screen_home.ids.lb_date.text = str(time.strftime("%d/%m/%Y", time.localtime()))
            screen_login.ids.lb_time.text = str(time.strftime("%H:%M:%S", time.localtime()))
            screen_login.ids.lb_date.text = str(time.strftime("%d/%m/%Y", time.localtime()))
            screen_menu.ids.lb_time.text = str(time.strftime("%H:%M:%S", time.localtime()))
            screen_menu.ids.lb_date.text = str(time.strftime("%d/%m/%Y", time.localtime()))
            screen_slm.ids.lb_time.text = str(time.strftime("%H:%M:%S", time.localtime()))
            screen_slm.ids.lb_date.text = str(time.strftime("%d/%m/%Y", time.localtime()))
            screen_wtm.ids.lb_time.text = str(time.strftime("%H:%M:%S", time.localtime()))
            screen_wtm.ids.lb_date.text = str(time.strftime("%d/%m/%Y", time.localtime()))
            screen_calibration.ids.lb_time.text = str(time.strftime("%H:%M:%S", time.localtime()))
            screen_calibration.ids.lb_date.text = str(time.strftime("%d/%m/%Y", time.localtime()))

            self.ids.lb_dash_pendaftaran.text = str(dt_dash_pendaftaran)
            self.ids.lb_dash_belum_uji.text = str(dt_dash_belum_uji)
            self.ids.lb_dash_sudah_uji.text = str(dt_dash_sudah_uji)

            screen_slm.ids.lb_no_antrian.text = str(dt_no_antrian)
            screen_slm.ids.lb_no_reg.text = str(dt_no_pol)
            screen_slm.ids.lb_no_uji.text = str(dt_no_uji)
            screen_slm.ids.lb_nama.text = str(dt_nama)
            screen_slm.ids.lb_jenis_kendaraan.text = str(dt_jenis_kendaraan)

            screen_wtm.ids.lb_no_antrian.text = str(dt_no_antrian)
            screen_wtm.ids.lb_no_reg.text = str(dt_no_pol)
            screen_wtm.ids.lb_no_uji.text = str(dt_no_uji)
            screen_wtm.ids.lb_nama.text = str(dt_nama)
            screen_wtm.ids.lb_jenis_kendaraan.text = str(dt_jenis_kendaraan)

            if(not flag_play):
                screen_slm.ids.bt_save.md_bg_color = colors['Green']['200']
                screen_slm.ids.bt_save.disabled = False
                screen_slm.ids.bt_reload.md_bg_color = colors['Red']['A200']
                screen_slm.ids.bt_reload.disabled = False
                screen_wtm.ids.bt_save.md_bg_color = colors['Green']['200']
                screen_wtm.ids.bt_save.disabled = False
                screen_wtm.ids.bt_reload.md_bg_color = colors['Red']['A200']
                screen_wtm.ids.bt_reload.disabled = False
            else:
                screen_slm.ids.bt_reload.disabled = True
                screen_slm.ids.bt_save.disabled = True
                screen_wtm.ids.bt_reload.disabled = True
                screen_wtm.ids.bt_save.disabled = True

            if(not flag_conn_stat):
                self.ids.lb_comm.color = colors['Red']['A200']
                self.ids.lb_comm.text = 'WTM Tidak Terhubung'
                screen_home.ids.lb_comm.color = colors['Red']['A200']
                screen_home.ids.lb_comm.text = 'WTM Tidak Terhubung'
                screen_login.ids.lb_comm.color = colors['Red']['A200']
                screen_login.ids.lb_comm.text = 'WTM Tidak Terhubung'
                screen_menu.ids.lb_comm.color = colors['Red']['A200']
                screen_menu.ids.lb_comm.text = 'WTM Tidak Terhubung'                
                screen_slm.ids.lb_comm.color = colors['Red']['A200']
                screen_slm.ids.lb_comm.text = 'WTM Tidak Terhubung'
                screen_wtm.ids.lb_comm.color = colors['Red']['A200']
                screen_wtm.ids.lb_comm.text = 'WTM Tidak Terhubung'
                screen_calibration.ids.lb_comm.color = colors['Red']['A200']
                screen_calibration.ids.lb_comm.text = 'WTM Tidak Terhubung'                
            else:
                self.ids.lb_comm.color = colors['Blue']['200']
                self.ids.lb_comm.text = 'WTM Terhubung'
                screen_home.ids.lb_comm.color = colors['Blue']['200']
                screen_home.ids.lb_comm.text = 'WTM Terhubung'
                screen_login.ids.lb_comm.color = colors['Blue']['200']
                screen_login.ids.lb_comm.text = 'WTM Terhubung'
                screen_menu.ids.lb_comm.color = colors['Blue']['200']
                screen_menu.ids.lb_comm.text = 'WTM Terhubung'                
                screen_slm.ids.lb_comm.color = colors['Blue']['200']
                screen_slm.ids.lb_comm.text = 'WTM Terhubung'
                screen_wtm.ids.lb_comm.color = colors['Blue']['200']
                screen_wtm.ids.lb_comm.text = 'WTM Terhubung'
                screen_calibration.ids.lb_comm.color = colors['Blue']['200']
                screen_calibration.ids.lb_comm.text = 'WTM Terhubung'

            if(count_starting <= 0):
                screen_slm.ids.lb_test_subtitle.text = "HASIL PENGUKURAN"
                screen_slm.ids.lb_sound.text = str(np.round(dt_slm_value, 2))
                screen_wtm.ids.lb_test_subtitle.text = "HASIL PENGUKURAN"
                screen_wtm.ids.lb_window_tint.text = str(np.round(dt_wtm_value, 2))

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
                    screen_slm.ids.lb_test_subtitle.text = "MEMULAI PENGUKURAN"
                    screen_slm.ids.lb_sound.text = str(count_starting)
                    screen_slm.ids.lb_info.text = "Silahkan Nyalakan Klakson Kendaraan"                    
                    screen_wtm.ids.lb_test_subtitle.text = "MEMULAI PENGUKURAN"
                    screen_wtm.ids.lb_window_tint.text = str(count_starting)
                    screen_wtm.ids.lb_info.text = "Silahkan Tekan Tombol Pengukuran Alat WTM"

            if(count_get_data <= 0):
                if(not flag_play):
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

                    if(dt_wtm_value <= STANDARD_MIN_WTM):
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
                    screen_slm.ids.lb_test_result.md_bg_color = colors['Gray']['500']
                    screen_slm.ids.lb_test_result.text = ""                    
                    screen_wtm.ids.lb_test_result.md_bg_color = "#EEEEEE"
                    screen_wtm.ids.lb_test_result.text = ""
            
            self.ids.bt_logout.disabled = False if dt_user != '' else True

            self.ids.lb_operator.text = f'Login Sebagai: {dt_user}' if dt_user != '' else 'Silahkan Login'
            screen_home.ids.lb_operator.text = f'Login Sebagai: {dt_user}' if dt_user != '' else 'Silahkan Login'
            screen_login.ids.lb_operator.text = f'Login Sebagai: {dt_user}' if dt_user != '' else 'Silahkan Login'
            screen_menu.ids.lb_operator.text = f'Login Sebagai: {dt_user}' if dt_user != '' else 'Silahkan Login'
            screen_slm.ids.lb_operator.text = f'Login Sebagai: {dt_user}' if dt_user != '' else 'Silahkan Login'
            screen_wtm.ids.lb_operator.text = f'Login Sebagai: {dt_user}' if dt_user != '' else 'Silahkan Login'
            screen_calibration.ids.lb_operator.text = f'Login Sebagai: {dt_user}' if dt_user != '' else 'Silahkan Login'

        except Exception as e:
            toast_msg = f'Error Update Display: {e}'
            toast(toast_msg)       

    def regular_update_connection(self, dt):
        global flag_conn_stat, wtm_device

        try:
            if wtm_device and wtm_device.is_open:
                flag_conn_stat = True
                return 
            found_port = False
            com_ports = list(ports.comports())
            for port in com_ports:
                if port.name == COM_PORT_WTM:
                    found_port = True
                    break 

            if found_port:
                if not (wtm_device and wtm_device.is_open):
                    print(f"Menemukan port {COM_PORT_WTM}. Mencoba menghubungkan...")
                    wtm_device = serial.Serial(
                        port=COM_PORT_WTM,
                        baudrate=115200, 
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE, 
                        bytesize=serial.EIGHTBITS, 
                        timeout=1 
                    )
                    flag_conn_stat = True
                    toast(f"WTM Terhubung di {COM_PORT_WTM}")
            else:
                if wtm_device and wtm_device.is_open:
                    wtm_device.close()
                wtm_device = None
                flag_conn_stat = False

        except serial.SerialException as e:
            toast(f"Error Serial: {e}")
            if wtm_device:
                wtm_device.close()
            wtm_device = None
            flag_conn_stat = False
        except Exception as e:
            toast(f'Error koneksi WTM: {e}')
            flag_conn_stat = False

    def exec_reload_database(self):
        global mydb
        try:
            mydb = mysql.connector.connect(host = DB_HOST,user = DB_USER,password = DB_PASSWORD,database = DB_NAME)
        except Exception as e:
            toast_msg = f'Error Initiate Database: {e}'
            toast(toast_msg)   

    def exec_reload_table(self):
        global mydb, db_antrian, db_merk
        global dt_dash_pendaftaran, dt_dash_belum_uji, dt_dash_sudah_uji

        try:
            tb_antrian = mydb.cursor(buffered=True)
            query = f"""
            SELECT
                noantrian, nopol, nouji, hlm_flag, slm_flag, wtm_flag,
                user, merk, type, idjeniskendaraan, jbb, bahan_bakar, warna
            FROM {TB_DATA}
            WHERE hlm_flag = 2 OR slm_flag = 2 OR wtm_flag = 2"""
            tb_antrian.execute(query)
            result_tb_antrian = tb_antrian.fetchall()
            print("==============================================")
            print(f"Hasil mentah dari fetchall(): {result_tb_antrian}")
            print(f"Jumlah baris yang diterima: {len(result_tb_antrian)}")
            print("==============================================")
            mydb.commit()
            db_antrian = np.array(result_tb_antrian).T
            db_pendaftaran = np.array(result_tb_antrian)
            dt_dash_pendaftaran = db_pendaftaran[:,3].size
            dt_dash_belum_uji = np.where(db_pendaftaran[:,3] == 0)[0].size
            dt_dash_sudah_uji = np.where(db_pendaftaran[:,3] == 1)[0].size

            tb_merk = mydb.cursor(buffered=True)
            tb_merk.execute(f"SELECT ID, DESCRIPTION FROM {TB_MERK}")
            result_tb_merk = tb_merk.fetchall()
            mydb.commit()
            db_merk = np.array(result_tb_merk)
        except Exception as e:
            toast_msg = f'Error Fetch Database: {e}'
            print(toast_msg)

        try:
            layout_list = self.ids.layout_list
            layout_list.clear_widgets(children=None)
        except Exception as e:
            toast_msg = f'Error Remove Widget: {e}'
            print(toast_msg)
        
        try:           
            layout_list = self.ids.layout_list
            for i in range(db_antrian[0,:].size):
                layout_list.add_widget(
                    MDCard(
                        MDLabel(text=f"{db_antrian[0, i]}", size_hint_x= 0.05),
                        MDLabel(text=f"{db_antrian[1, i]}", size_hint_x= 0.08),
                        MDLabel(text=f"{db_antrian[2, i]}", size_hint_x= 0.08),
                        MDLabel(text='Lulus' if (int(db_antrian[3, i]) == 1) else 'Tidak Lulus' if (int(db_antrian[3, i]) == 0) else 'Belum Uji', size_hint_x= 0.07),
                        MDLabel(text='Lulus' if (int(db_antrian[4, i]) == 1) else 'Tidak Lulus' if (int(db_antrian[4, i]) == 0) else 'Belum Uji', size_hint_x= 0.07),
                        MDLabel(text='Lulus' if (int(db_antrian[5, i]) == 1) else 'Tidak Lulus' if (int(db_antrian[5, i]) == 0) else 'Belum Uji', size_hint_x= 0.07),
                        MDLabel(text=f"{db_antrian[6, i]}", size_hint_x= 0.12),
                        MDLabel(text=f"{db_merk[np.where(db_merk == db_antrian[7, i])[0][0],1]}", size_hint_x= 0.08),
                        MDLabel(text=f"{db_antrian[8, i]}", size_hint_x= 0.08),
                        MDLabel(text=f"{db_antrian[9, i]}", size_hint_x= 0.15),
                        MDLabel(text=f"{db_antrian[10, i]}", size_hint_x= 0.05),
                        MDLabel(text=f"{db_antrian[11, i]}", size_hint_x= 0.08),
                        MDLabel(text=f"{db_antrian[12, i]}", size_hint_x= 0.08),

                        ripple_behavior = True,
                        on_press = self.on_antrian_row_press,
                        padding = 20,
                        id=f"card_antrian{i}",
                        size_hint_y=None,
                        height="60dp",
                        )
                    )

        except Exception as e:
            toast_msg = f'Error Reload Table: {e}'
            print(toast_msg)

    def reset_data(self):
        global db_slm_value, count_starting, count_get_data, dt_slm_value        
        count_starting = COUNT_STARTING
        count_get_data = COUNT_ACQUISITION
        dt_slm_value = 0.0
        db_slm_value = np.array([0.0])

    def regular_get_data_hlm(self, dt):
        global flag_play
        global dt_hlm_left_value, dt_hlm_right_value, dt_hlm_diff_left_value, dt_hlm_diff_right_value
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
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    numpy_data = np.frombuffer(data, dtype=np.int16)
                    normalized_data = numpy_data / 32768.0
                    rms_amplitude = np.sqrt(np.mean(normalized_data**2))
                    sound_level_db = konversi_ke_db(rms_amplitude)
                    dt_slm_value = max(dt_slm_value, sound_level_db)

                except Exception as audio_err:
                    print(f"Audio reading error: {audio_err}")

        except Exception as e:
            toast_msg = f'error get data: {e}'
            print(toast_msg)    

    def regular_get_data_wtm(self, dt):
        global flag_play, dt_wtm_value, count_starting, count_get_data, wtm_device
        global wtm_arr_val_ref, wtm_arr_data_ref

        try:
            if not flag_play:
                Clock.unschedule(self.regular_get_data_wtm)
                return
            if count_starting > 0:
                count_starting -= 1
                return  
            if count_get_data > 0:
                count_get_data -= 1
            else: 
                flag_play = False
                Clock.unschedule(self.regular_get_data_wtm)
                return

            if not (wtm_device and wtm_device.is_open):
                toast("Koneksi WTM terputus.")
                flag_play = False
                Clock.unschedule(self.regular_get_data_wtm)
                return

            line = wtm_device.readline().decode('utf-8').strip()
            
            data_bersih = ""
            if "Parsing data penting:" in line:
                data_bersih = line.split("Parsing data penting:")[1].strip()
            elif line:
                data_bersih = line

            if data_bersih:
                arr_data_masuk = np.array(data_bersih.split())
                panjang_data_masuk = len(arr_data_masuk)
                
                match_found = False
                if wtm_arr_val_ref is not None and wtm_arr_data_ref is not None:
                    for i in range(len(wtm_arr_val_ref)):
                        baris_referensi = wtm_arr_data_ref[i]
                        if len(baris_referensi) >= panjang_data_masuk:
                            subset_referensi = baris_referensi[:panjang_data_masuk]
                            
                            if np.array_equal(arr_data_masuk, subset_referensi):
                                dt_wtm_value = float(wtm_arr_val_ref[i])
                                match_found = True
                                break 
                
        except Exception as e:
            toast(f"Error get data WTM: {e}", duration=4)
            print(f"ERROR di regular_get_data_wtm: {e}")
            flag_play = False
            Clock.unschedule(self.regular_get_data_wtm)

    def load_wtm_reference_data(self):
        global wtm_arr_val_ref, wtm_arr_data_ref

        if wtm_arr_val_ref is not None:
            return

        CSV_PATH = os.path.join(application_path, 'data', 'sample_data_wtm.csv')
        if not os.path.exists(CSV_PATH):
            toast(f"ERROR: File referensi WTM tidak ditemukan!", duration=4)
            return

        try:
            toast("Memuat file referensi WTM...")
            arr_ref = np.genfromtxt(CSV_PATH, delimiter=";", dtype=str, skip_header=1, encoding='utf-8')
            wtm_arr_val_ref = arr_ref[:, 0]
            wtm_arr_data_ref = arr_ref[:, 1:]
            toast(f"File referensi WTM berhasil dimuat.")
        except Exception as e:
            toast(f"Gagal memuat CSV WTM: {e}", duration=4)
            print(f"ERROR saat memuat CSV WTM: {e}")

    def exec_start_hlm(self):
        global flag_play
        if not flag_play:
            Clock.schedule_interval(self.regular_get_data_hlm, GET_DATA_INTERVAL)
            self.manager.current = 'screen_hlm'
            flag_play = True

    def exec_start_slm(self):
        global flag_play, stream
        if not flag_play:
            try:
                if not stream.is_active():
                    stream.start_stream()
                Clock.schedule_interval(self.regular_get_data_slm, GET_DATA_INTERVAL)
                self.manager.current = 'screen_slm'
                flag_play = True
            except Exception as e:
                toast(f"Error memulai audio stream: {e}")

    def exec_start_wtm(self):
        global flag_play
        if not flag_play:
            Clock.schedule_interval(self.regular_get_data_wtm, GET_DATA_INTERVAL)
            self.manager.current = 'screen_wtm'
            flag_play = True

    def exec_logout(self):
        global dt_user

        dt_user = ""
        self.screen_manager.current = 'screen_login'

    def exec_navigate_home(self):
        try:
            self.screen_manager.current = 'screen_home'

        except Exception as e:
            toast_msg = f'Error Navigate to Home Screen: {e}'
            toast(toast_msg)        

    def exec_navigate_login(self):
        global dt_user
        try:
            if (dt_user == ""):
                self.screen_manager.current = 'screen_login'
            else:
                toast(f"Anda sudah login sebagai {dt_user}")

        except Exception as e:
            toast_msg = f'Error Navigate to Login Screen: {e}'
            toast(toast_msg)    

    def exec_navigate_main(self):
        try:
            self.screen_manager.current = 'screen_main'

        except Exception as e:
            toast_msg = f'Error Navigate to Main Screen: {e}'
            toast(toast_msg)   

class ScreenMenu(MDScreen):
    def __init__(self, **kwargs):
        super(ScreenMenu, self).__init__(**kwargs)

    def on_enter(self):
        """HANYA mengisi label informasi kendaraan."""
        global dt_no_antrian, dt_no_pol, dt_no_uji, dt_nama, dt_jenis_kendaraan
        global dt_merk, dt_type, dt_jbb, dt_bahan_bakar, dt_warna
        
        try:
            self.ids.lb_no_antri.text = str(dt_no_antrian)
            self.ids.lb_no_pol.text = str(dt_no_pol)
            self.ids.lb_no_uji.text = str(dt_no_uji)
            self.ids.lb_merk.text = str(dt_merk)
            self.ids.lb_type.text = str(dt_type)
            self.ids.lb_jns_kend.text = str(dt_jenis_kendaraan)
            self.ids.lb_jbb.text = str(dt_jbb)
            # self.ids.lb_brt_ksg.text = "-"
            # self.ids.lb_sts_uji.text = str(dt_sts_uji)
            self.ids.lb_bhn_bkr.text = str(dt_bahan_bakar)
            self.ids.lb_warna.text = str(dt_warna)
            self.ids.lb_test_result.text = ""
        except Exception as e:
            print(f"Error saat update label di ScreenMenu: {e}")
            toast("Gagal memuat data kendaraan ke menu.")

    def exec_start_hlm(self):
        """Memberi perintah ke ScreenMain untuk memulai tes HLM."""
        screen_main = self.manager.get_screen('screen_main')
        screen_main.exec_start_hlm()

    def exec_start_slm(self):
        """Memberi perintah ke ScreenMain untuk memulai tes SLM."""
        screen_main = self.manager.get_screen('screen_main')
        screen_main.exec_start_slm()
        
    def exec_start_wtm(self):
        """Memberi perintah ke ScreenMain untuk memulai tes WTM."""
        screen_main = self.manager.get_screen('screen_main')
        screen_main.exec_start_wtm()

    def exec_navigate_main(self):
        """Kembali ke layar utama (daftar antrian)."""
        self.manager.current = 'screen_main'
            
class ScreenHLM(MDScreen):
    def __init__(self, **kwargs):
        super(ScreenHLM, self).__init__(**kwargs)
        self.capture = None
        self.camera_event = None
        self.camera_is_on = False
        self.test_beam = 'jauh'
        self.test_side = 'kiri'

        # PERBAIKAN: Struktur data baru untuk menyimpan hasil lebih detail
        self.test_results = {}
        self._reset_test_results()

        self.current_cd = 0
        self.current_dev_h = 0
        self.current_dev_v = 0
        self.countdown_seconds = config.getint('headlamp_settings', 'count_starting_lamp', fallback=5)
        self.countdown_event = None

        try:
            config.read(config_full_path)
            self.TEST_DISTANCE_METERS = config.getfloat('headlamp_settings', 'test_distance_meters')
            self.CAM_WIDTH = config.getint('headlamp_settings', 'camera_width')
            self.CAM_HEIGHT = config.getint('headlamp_settings', 'camera_height')
            self.REF_POINT_X = config.getint('headlamp_settings', 'ref_point_x')
            self.REF_POINT_Y = config.getint('headlamp_settings', 'ref_point_y')
            self.PIXELS_PER_DEGREE_HORIZONTAL = config.getfloat('headlamp_settings', 'pixels_per_degree_horizontal')
            self.MM_PER_PIXEL_VERTICAL = config.getfloat('headlamp_settings', 'mm_per_pixel_vertical')
            self.MIN_CANDELA_THRESHOLD = config.getfloat('headlamp_settings', 'min_candela_lulus')
            self.MAX_DEVIATION_RIGHT_DEG = config.getfloat('headlamp_settings', 'max_deviation_right_deg')
            self.MAX_DEVIATION_LEFT_DEG = config.getfloat('headlamp_settings', 'max_deviation_left_deg')
            self.MAX_VERTICAL_DEVIATION_PERCENT = config.getfloat('headlamp_settings', 'max_vertical_deviation_percent')
            self.LUX_TO_CANDELA_FACTOR = self.TEST_DISTANCE_METERS ** 2
            Logger.info(f"{self.name}: Pengaturan Headlamp berhasil dimuat.")
        except Exception as e:
            toast("Gagal memuat config.ini, menggunakan nilai default.")
            Logger.error(f"{self.name}: Error saat membaca config.ini: {e}")
            # Fallback values
            self.TEST_DISTANCE_METERS, self.CAM_WIDTH, self.CAM_HEIGHT = 1.0, 640, 480
            self.REF_POINT_X, self.REF_POINT_Y = 320, 240
            self.PIXELS_PER_DEGREE_HORIZONTAL, self.MM_PER_PIXEL_VERTICAL = 50.0, 1.5
            self.MIN_CANDELA_THRESHOLD = 12000.0
            self.MAX_DEVIATION_RIGHT_DEG, self.MAX_DEVIATION_LEFT_DEG = 0.57, 1.15
            self.MAX_VERTICAL_DEVIATION_PERCENT = 1.3
            self.LUX_TO_CANDELA_FACTOR = self.TEST_DISTANCE_METERS ** 2

        Clock.schedule_once(self.delayed_init, 1)

    def delayed_init(self, dt):
        self.ids.lb_title.text = APP_TITLE
        self.ids.lb_subtitle.text = APP_SUBTITLE
        self.ids.img_pemkab.source = f'assets/images/{IMG_LOGO_PEMKAB}'
        self.ids.img_dishub.source = f'assets/images/{IMG_LOGO_DISHUB}'
        self.ids.lb_pemkab.text = LB_PEMKAB
        self.ids.lb_dishub.text = LB_DISHUB
        self.ids.lb_unit.text = LB_UNIT
        self.ids.lb_unit_address.text = LB_UNIT_ADDRESS

    def _reset_test_results(self):
        """Mereset struktur data untuk menyimpan hasil yang lebih detail."""
        default_result = {'cd': 0, 'dev_h': 0, 'dev_v': 0,
                          'intensity_flag': 2, 'deviation_flag': 2, 'status': 2}
        self.test_results = {
            'jauh_kiri': default_result.copy(),
            'jauh_kanan': default_result.copy(),
            'dekat_kiri': default_result.copy(),
            'dekat_kanan': default_result.copy()
        }


    def on_leave(self, *args):
        if self.camera_is_on: self.stop_camera()
        if self.countdown_event: self.countdown_event.cancel(); self.countdown_event = None


    def on_enter(self, *args):
        """Dipanggil saat layar ditampilkan."""
        try:
            config.read(config_full_path)
            self.INTENSITY_SLOPE = config.getfloat('camera_calibration', 'intensity_slope')
            self.INTENSITY_INTERCEPT = config.getfloat('camera_calibration', 'intensity_intercept')
            self.CAMERA_EXPOSURE = config.getfloat('camera_calibration', 'exposure', fallback=-4)
        except Exception:
            self.INTENSITY_SLOPE, self.INTENSITY_INTERCEPT, self.CAMERA_EXPOSURE = 1.0, 0.0, -4
        try:
            self.ids.lb_no_antrian.text = str(dt_no_antrian)
            self.ids.lb_no_pol.text = str(dt_no_pol)
            self.ids.lb_no_uji.text = str(dt_no_uji)
        except Exception as e:
            Logger.error(f"{self.name}: Gagal mengisi label identitas - {e}")
        
        self._reset_test_results()
        self.ids.camera_view.texture = None
        self.ids.lb_countdown.text = ""
        self.ids.lb_test_result.text = "-"
        
        # Atur status DAN warna default saat layar dibuka
        self.select_beam('jauh')
        self.select_side('kiri')

    def select_beam(self, beam_type):
        """Mengatur jenis lampu dan mengubah warna background, teks, dan ikon."""
        self.test_beam = beam_type
        
        selected_color = self.theme_cls.colors["Blue"]["200"] 
        unselected_color = (0.9, 0.9, 0.9, 1)
        
        # Atur warna background
        self.ids.btn_jauh.md_bg_color = selected_color if beam_type == 'jauh' else unselected_color
        self.ids.btn_dekat.md_bg_color = selected_color if beam_type == 'dekat' else unselected_color
        
        # PERBAIKAN: Atur warna teks DAN ikon agar kontras
        self.ids.btn_jauh.text_color = "white" if beam_type == 'jauh' else "black"
        self.ids.btn_jauh.icon_color = "white" if beam_type == 'jauh' else "black"
        
        self.ids.btn_dekat.text_color = "white" if beam_type == 'dekat' else "black"
        self.ids.btn_dekat.icon_color = "white" if beam_type == 'dekat' else "black"
            
        self._update_info_panel()

    def select_side(self, side_type):
        """Mengatur sisi lampu dan mengubah warna background, teks, dan ikon."""
        self.test_side = side_type
        
        selected_color = self.theme_cls.colors["Blue"]["200"]
        unselected_color = (0.9, 0.9, 0.9, 1)
        
        # Atur warna background
        self.ids.btn_kiri.md_bg_color = selected_color if side_type == 'kiri' else unselected_color
        self.ids.btn_kanan.md_bg_color = selected_color if side_type == 'kanan' else unselected_color
        
        # PERBAIKAN: Atur warna teks DAN ikon agar kontras
        self.ids.btn_kiri.text_color = "white" if side_type == 'kiri' else "black"
        self.ids.btn_kiri.icon_color = "white" if side_type == 'kiri' else "black"

        self.ids.btn_kanan.text_color = "white" if side_type == 'kanan' else "black"
        self.ids.btn_kanan.icon_color = "white" if side_type == 'kanan' else "black"
            
        self._update_info_panel()

    def _update_info_panel(self):
            """Memperbarui semua label informasi di panel kanan, termasuk status kelulusan."""
            key = f"{self.test_beam}_{self.test_side}"
            result = self.test_results.get(key, {})
            
            # Update info bagian dan nilai terukur (tetap sama)
            bagian_uji = f"Lampu {self.test_beam.capitalize()} {self.test_side.capitalize()}"
            self.ids.lb_info_bagian.text = bagian_uji
            self.ids.lb_info_daya.text = f"{result.get('cd', 0):.0f} Cdl"
            dev_h, dev_v = result.get('dev_h', 0), result.get('dev_v', 0)
            dev_h_text = f"{abs(dev_h):.2f}° {'Kiri' if dev_h < 0 else 'Kanan'}"
            dev_v_text = f"{abs(dev_v):.2f}% {'Bawah' if dev_v < 0 else 'Atas'}"
            self.ids.lb_info_penyimpangan.text = f"H: {dev_h_text} | V: {dev_v_text}"

            # PERBAIKAN: Logika baru untuk mengisi label status
            # Status Daya Pancar
            intensity_flag = result.get('intensity_flag', 2) # 2 = Belum diuji
            if intensity_flag == 1:
                self.ids.lb_info_daya_status.text = "(LULUS)"
                self.ids.lb_info_daya_status.text_color = (0.2, 0.8, 0.2, 1) # Hijau
            elif intensity_flag == 0:
                self.ids.lb_info_daya_status.text = "(TIDAK LULUS)"
                self.ids.lb_info_daya_status.text_color = (1, 0.2, 0.2, 1) # Merah
            else:
                self.ids.lb_info_daya_status.text = "(-)"
                self.ids.lb_info_daya_status.text_color = "white"

            # Status Penyimpangan
            deviation_flag = result.get('deviation_flag', 2) # 2 = Belum diuji
            if deviation_flag == 1:
                self.ids.lb_info_penyimpangan_status.text = "(LULUS)"
                self.ids.lb_info_penyimpangan_status.text_color = (0.2, 0.8, 0.2, 1) # Hijau
            elif deviation_flag == 0:
                self.ids.lb_info_penyimpangan_status.text = "(TIDAK LULUS)"
                self.ids.lb_info_penyimpangan_status.text_color = (1, 0.2, 0.2, 1) # Merah
            else:
                self.ids.lb_info_penyimpangan_status.text = "(-)"
                self.ids.lb_info_penyimpangan_status.text_color = "white"

    def exec_open_camera(self):
        if self.camera_is_on: self.stop_camera()
        else: self.start_camera()

    def exec_start_test(self):
        if not self.camera_is_on: toast("Kamera belum dibuka. Tekan 'BUKA' terlebih dahulu."); return
        if self.countdown_event: toast("Pengujian sedang berjalan."); return
        self.countdown_value = self.countdown_seconds
        self.ids.lb_countdown.text = str(self.countdown_value)
        self.countdown_event = Clock.schedule_interval(self._update_countdown, 1)

    def _update_countdown(self, dt):
        self.countdown_value -= 1
        self.ids.lb_countdown.text = str(self.countdown_value) if self.countdown_value > 0 else "Selesai!"
        if self.countdown_value <= 0: self._finish_test()

    def _finish_test(self):
        if self.countdown_event: self.countdown_event.cancel(); self.countdown_event = None
        key = f"{self.test_beam}_{self.test_side}"
        
        # PERBAIKAN: Panggil fungsi baru untuk mendapatkan semua status
        intensity_flag, deviation_flag, overall_status = self._calculate_pass_fail(
            self.current_cd, self.current_dev_h, self.current_dev_v, self.test_side)

        # Simpan semua data ke dictionary
        self.test_results[key]['cd'] = self.current_cd
        self.test_results[key]['dev_h'] = self.current_dev_h
        self.test_results[key]['dev_v'] = self.current_dev_v
        self.test_results[key]['intensity_flag'] = intensity_flag
        self.test_results[key]['deviation_flag'] = deviation_flag
        self.test_results[key]['status'] = overall_status

        # Update UI
        self.ids.lb_test_result.text = "LULUS" if overall_status else "TIDAK LULUS"
        self.ids.lb_test_result.md_bg_color = (0,0.7,0,1) if overall_status else (0.9,0,0,1)
        self._update_info_panel()
        Clock.schedule_once(lambda dt: setattr(self.ids.lb_countdown, 'text', ''), 1)

    def start_camera(self):
        self.capture = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        if not self.capture.isOpened(): toast("Error: Tidak dapat membuka kamera."); self.capture = None; return
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.CAM_WIDTH)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.CAM_HEIGHT)
        self.capture.set(cv2.CAP_PROP_EXPOSURE, self.CAMERA_EXPOSURE)
        self.camera_event = Clock.schedule_interval(self.update_camera_feed, 1.0 / 30.0)
        self.camera_is_on = True

    def stop_camera(self):
        if self.camera_event: self.camera_event.cancel(); self.camera_event = None
        if self.capture: self.capture.release(); self.capture = None
        self.camera_is_on = False
        self.ids.camera_view.texture = None

    def update_camera_feed(self, dt):
        if not self.capture: return
        ret, frame = self.capture.read()
        if not ret: return
        processed_frame = self.analyze_frame(frame)
        buf = cv2.flip(processed_frame, 0).tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.ids.camera_view.texture = texture

    def convert_pixel_to_lux(self, pixel_value):
        return max(0, (self.INTENSITY_SLOPE * pixel_value) + self.INTENSITY_INTERCEPT)

    def convert_lux_to_candela(self, lux_value):
        return lux_value * self.LUX_TO_CANDELA_FACTOR

    def analyze_frame(self, frame):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        display_frame = frame
        (_minVal, _maxVal, _minLoc, maxLoc) = cv2.minMaxLoc(gray_frame)
        beam_center_x, beam_center_y = maxLoc
        roi_size = 50
        roi_x, roi_y = max(0, beam_center_x - roi_size // 2), max(0, beam_center_y - roi_size // 2)
        roi_gray = gray_frame[roi_y : roi_y + roi_size, roi_x : roi_x + roi_size]
        if roi_gray.size > 0:
            mean_pixel_val = cv2.mean(roi_gray)[0]
            self.current_cd = self.convert_lux_to_candela(self.convert_pixel_to_lux(mean_pixel_val))
            self.current_dev_h = (beam_center_x - self.REF_POINT_X) / self.PIXELS_PER_DEGREE_HORIZONTAL
            pixel_dev_y = self.REF_POINT_Y - beam_center_y
            dev_in_mm = pixel_dev_y * self.MM_PER_PIXEL_VERTICAL
            self.current_dev_v = (dev_in_mm / (self.TEST_DISTANCE_METERS * 1000)) * 100
        cv2.circle(display_frame, (self.REF_POINT_X, self.REF_POINT_Y), 10, (255, 0, 0), 2)
        cv2.circle(display_frame, maxLoc, 15, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Daya: {self.current_cd:.0f} cd", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
        return display_frame

    # PERBAIKAN: Fungsi ini sekarang hanya menghitung dan mengembalikan flag
    def _calculate_pass_fail(self, cd, dev_h, dev_v, side):
        """Menghitung dan mengembalikan flag kelulusan terpisah untuk daya dan deviasi."""
        intensity_pass = cd >= self.MIN_CANDELA_THRESHOLD
        
        horizontal_pass = False
        if side == 'kiri' and abs(dev_h) <= self.MAX_DEVIATION_LEFT_DEG:
            horizontal_pass = True
        elif side == 'kanan' and abs(dev_h) <= self.MAX_DEVIATION_RIGHT_DEG:
            horizontal_pass = True
            
        vertical_pass = abs(dev_v) <= self.MAX_VERTICAL_DEVIATION_PERCENT
        
        deviation_pass = horizontal_pass and vertical_pass
        overall_status = intensity_pass and deviation_pass

        return (1 if intensity_pass else 0, 
                1 if deviation_pass else 0, 
                1 if overall_status else 0)

    def exec_save(self):
            if not dt_no_uji:
                toast("Tidak ada data kendaraan yang dipilih.")
                return

            # Hanya ambil data dari lampu JAUH
            jk = self.test_results['jauh_kanan']
            jl = self.test_results['jauh_kiri']

            # Kumpulkan semua flag individu ke dalam satu list untuk pengecekan
            all_flags = [
                jk['intensity_flag'],
                jk['deviation_flag'],
                jl['intensity_flag'],
                jl['deviation_flag']
            ]

            # Logika baru dengan 3 status: 2 (Belum Uji), 1 (Lulus), 0 (Tidak Lulus)
            if 2 in all_flags:
                final_hlm_flag = 2
            elif all(flag == 1 for flag in all_flags):
                final_hlm_flag = 1
            else:
                final_hlm_flag = 0
            
            # Tambahkan baris ini untuk mendapatkan waktu dan user saat ini
            hlm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
            hlm_user = dt_hlm_user

            try:
                screen_main = self.manager.get_screen('screen_main')
                screen_main.exec_reload_database()
                cursor = mydb.cursor()

                # Query SQL diperbarui dengan hlm_user dan hlm_post
                query = f"""
                    UPDATE {TB_DATA} SET
                        hlm_right_value = %s, hlm_right_flag = %s,
                        hlm_diff_right_value = %s, hlm_diff_right_flag = %s,
                        
                        hlm_left_value = %s, hlm_left_flag = %s,
                        hlm_diff_left_value = %s, hlm_diff_left_flag = %s,
                        
                        hlm_user = %s,
                        hlm_post = %s,
                        hlm_flag = %s
                    WHERE nouji = %s
                """
                
                # Values diperbarui dengan hlm_user dan hlm_post
                values = (
                    jk['cd'], jk['intensity_flag'], jk['dev_h'], jk['deviation_flag'],
                    jl['cd'], jl['intensity_flag'], jl['dev_h'], jl['deviation_flag'],
                    hlm_user,
                    hlm_post,
                    final_hlm_flag,
                    dt_no_uji
                )
                
                cursor.execute(query, values)
                mydb.commit()
                
                toast("Data Headlamp berhasil disimpan!")
                Logger.info(f"Data headlamp (jauh) untuk nouji {dt_no_uji} berhasil disimpan.")
                self.manager.current = 'screen_menu'

            except Exception as e:
                toast("Gagal menyimpan data ke database.")
                Logger.error(f"{self.name}: Error saat menyimpan: {e}")

    def exec_navigate_main(self):
        """Fungsi untuk kembali ke layar menu dari layar HLM."""
        self.manager.current = 'screen_menu'

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
            Clock.schedule_interval(screen_main.regular_get_data_slm, GET_DATA_INTERVAL)
            flag_play = True

    def exec_reload(self):
        global flag_play
        toast("Mengulang pengujian SLM...")
        try:
            screen_main = self.screen_manager.get_screen('screen_main')
            self.reset_data()
            self.ids.bt_reload.disabled = True
            if not flag_play:
                stream.start_stream()
                Clock.schedule_interval(screen_main.regular_get_data_slm, GET_DATA_INTERVAL)
                flag_play = True
        except Exception as e:
            toast(f"ERROR saat reload SLM: {e}", duration=4)

    def exec_save(self):
        global mydb, dt_slm_flag, dt_slm_value, dt_slm_user, dt_slm_post, dt_no_antrian
        
        try:
            toast("Menyimpan hasil SLM...")
            self.screen_manager.get_screen('screen_main').exec_reload_database()
            
            self.ids.bt_save.disabled = True
            mycursor = mydb.cursor(buffered=True)
            sql = f"UPDATE {TB_DATA} SET slm_flag = %s, slm_value = %s, slm_user = %s, slm_post = %s WHERE noantrian = %s"
            sql_slm_flag = (1 if dt_slm_flag == "Lulus" else 0)
            dt_slm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
            sql_val = (sql_slm_flag, float(dt_slm_value), dt_slm_user, dt_slm_post, dt_no_antrian)

            print(f"DEBUG SAVE | Nilai yang akan disimpan: {sql_val}") 
            mycursor.execute(sql, sql_val)
            mydb.commit()
            toast("Hasil SLM berhasil disimpan!", duration=3)
            stream.stop_stream()
            self.exec_navigate_menu()
            
        except Exception as e:
            print(f" KESALAHAN SPESIFIK SAAT MENYIMPAN SLM: {e}")
            toast(f"ERROR: {e}", duration=5)
            self.ids.bt_save.disabled = False

    def exec_navigate_menu(self):
        global flag_play
        try:
            if stream.is_active():
                stream.stop_stream() 
            self.reset_data()
            flag_play = False
            self.manager.current = 'screen_menu'
        except Exception as e:
            toast(f"ERROR kembali ke menu: {e}", duration=4) 



class ScreenWTM(MDScreen):        
    def __init__(self, **kwargs):
        super(ScreenWTM, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init, 2)

    def delayed_init(self, dt):
        pass

    def exec_start(self):
        global flag_play
        global count_starting, count_get_data

        screen_main = self.screen_manager.get_screen('screen_main')

        count_starting = COUNT_STARTING
        count_get_data = COUNT_ACQUISITION

        if(not flag_play):
            Clock.schedule_interval(screen_main.regular_get_data_wtm, GET_DATA_INTERVAL)
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
            Clock.schedule_interval(screen_main.regular_get_data_wtm, GET_DATA_INTERVAL)
            flag_play = True

    def exec_save(self):
        global mydb, dt_wtm_flag, dt_wtm_value, dt_wtm_user, dt_wtm_post, dt_no_antrian

        try:
            self.screen_manager.get_screen('screen_main').exec_reload_database()
            self.ids.bt_save.disabled = True
            mycursor = mydb.cursor(buffered=True)
            
            sql = f"UPDATE {TB_DATA} SET wtm_flag = %s, wtm_value = %s, wtm_user = %s, wtm_post = %s WHERE noantrian = %s"
            sql_wtm_flag = (1 if dt_wtm_flag == "Lulus" else 0)
            dt_wtm_post = str(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
            safe_wtm_value = float(str(dt_wtm_value).replace(',', '.'))
            sql_val = (sql_wtm_flag, safe_wtm_value, dt_wtm_user, dt_wtm_post, dt_no_antrian)

            print(f"DEBUG SAVE WTM | Nilai yang akan disimpan: {sql_val}") 
            
            mycursor.execute(sql, sql_val)
            mydb.commit()
            toast("Hasil WTM berhasil disimpan!", duration=3)
            self.exec_navigate_menu()
            
        except Exception as e:
            print(f"KESALAHAN SPESIFIK SAAT MENYIMPAN WTM: {e}")
            toast(f"ERROR: {e}", duration=5)
            self.ids.bt_save.disabled = False

    def exec_navigate_menu(self):
        global flag_play      
        global count_starting, count_get_data
        try:
            flag_play = False  
            self.screen_manager.current = 'screen_menu'
        except Exception as e:
            toast(f"Error navigating to menu: {e}")

class ScreenCalibration(MDScreen):
    def __init__(self, **kwargs):
        super(ScreenCalibration, self).__init__(**kwargs)
        self.capture = None
        self.camera_event = None
        self.camera_is_on = False
        self.calibration_data = []
        self.current_max_val = 0
        
        # Nilai kalibrasi default
        self.INTENSITY_SLOPE = 1.0
        self.INTENSITY_INTERCEPT = 0.0
        
        Clock.schedule_once(self.delayed_init, 1)

    def delayed_init(self, dt):
        """Inisialisasi label dan gambar header/footer."""
        self.ids.lb_title.text = APP_TITLE
        self.ids.lb_subtitle.text = APP_SUBTITLE
        self.ids.img_pemkab.source = f'assets/images/{IMG_LOGO_PEMKAB}'
        self.ids.img_dishub.source = f'assets/images/{IMG_LOGO_DISHUB}'
        self.ids.lb_pemkab.text = LB_PEMKAB
        self.ids.lb_dishub.text = LB_DISHUB
        self.ids.lb_unit.text = LB_UNIT
        self.ids.lb_unit_address.text = LB_UNIT_ADDRESS

    def on_enter(self):
        """Aksi saat layar dibuka: muat konfigurasi dan nyalakan kamera."""
        self.load_calibration_values()
        self.clear_data()
        self.start_camera()
        if not self.capture:
            toast("Kamera tidak ditemukan. Kembali ke menu utama.")
            Clock.schedule_once(lambda dt: self.exec_navigate_main(), 2)

    def on_leave(self):
        """Aksi saat layar ditutup: matikan kamera."""
        self.stop_camera()

    def start_camera(self):
        """Membuka device kamera dan memulai feed."""
        if self.camera_is_on:
            return
            
        self.capture = cv2.VideoCapture(1, cv2.CAP_DSHOW)

        if not self.capture.isOpened():
            toast("Error: Tidak dapat membuka kamera.")
            self.capture = None
            return
            
        # Atur properti kamera
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.capture.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0) 
        self.capture.set(cv2.CAP_PROP_AUTO_WB, 0) 

        # Atur exposure awal dari slider
        initial_exposure = self.ids.exposure_slider.value
        self.capture.set(cv2.CAP_PROP_EXPOSURE, initial_exposure)
        self.ids.exposure_label.text = f"Exposure: {int(initial_exposure)}"
        
        self.camera_event = Clock.schedule_interval(self.update_camera_feed, 1.0 / 30.0)
        self.camera_is_on = True

    def stop_camera(self):
        """Menghentikan feed kamera dan melepaskan device."""
        if self.camera_event:
            self.camera_event.cancel()
            self.camera_event = None
        if self.capture:
            self.capture.release()
            self.capture = None
        self.camera_is_on = False

    def on_exposure_change(self, value):
        """Dipanggil saat slider exposure diubah."""
        if self.capture and self.camera_is_on:
            self.capture.set(cv2.CAP_PROP_EXPOSURE, value)
            self.ids.exposure_label.text = f"Exposure: {int(value)}"
            
    def update_camera_feed(self, dt):
        """Membaca frame dari kamera, memprosesnya, dan menampilkannya di UI."""
        if not self.capture or not self.camera_is_on:
            return
        
        ret, frame = self.capture.read()
        if not ret:
            Logger.warning("Gagal membaca frame dari kamera.")
            return

        processed_frame = self.analyze_frame_for_calibration(frame)
        
        # Konversi frame OpenCV ke tekstur Kivy
        buf = cv2.flip(processed_frame, 0).tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.ids.camera_view.texture = texture

    def load_calibration_values(self):
        """Memuat nilai slope dan intercept dari config.ini."""
        try:
            config.read(config_full_path)
            self.INTENSITY_SLOPE = float(config.get('camera_calibration', 'intensity_slope'))
            self.INTENSITY_INTERCEPT = float(config.get('camera_calibration', 'intensity_intercept'))
            toast("Konfigurasi kalibrasi dimuat.")
            Logger.info(f"{self.name}: Kalibrasi dimuat: Slope={self.INTENSITY_SLOPE}, Intercept={self.INTENSITY_INTERCEPT}")
        except (configparser.NoSectionError, configparser.NoOptionError):
            Logger.warning(f"{self.name}: Sesi [camera_calibration] tidak ditemukan. Menggunakan nilai default.")
            self.INTENSITY_SLOPE = 1.0
            self.INTENSITY_INTERCEPT = 0.0

    def convert_pixel_to_lux(self, pixel_value):
        """Mengonversi nilai piksel ke lux menggunakan slope dan intercept saat ini."""
        return max(0, (self.INTENSITY_SLOPE * pixel_value) + self.INTENSITY_INTERCEPT)

    def analyze_frame_for_calibration(self, frame):
        """Menganalisis frame di area tengah untuk mendapatkan nilai piksel dan visualisasi."""
        (frame_height, frame_width) = frame.shape[:2]
        roi_size = 200  # Ukuran kotak ROI (200x200 piksel)
        
        roi_x = int((frame_width / 2) - (roi_size / 2))
        roi_y = int((frame_height / 2) - (roi_size / 2))

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        roi_gray = gray_frame[roi_y : roi_y + roi_size, roi_x : roi_x + roi_size]

        mean_val = cv2.mean(roi_gray)[0] 
        self.current_max_val = int(mean_val)

        calibrated_lux = self.convert_pixel_to_lux(self.current_max_val)

        try:
            self.ids.live_pixel_value.text = f"Nilai Piksel Mentah: [b]{self.current_max_val}[/b]"
            self.ids.calibrated_lux_value.text = f"Lux Terkalibrasi: [b]{calibrated_lux:.2f} lx[/b]"
        except KeyError:
            pass # Mencegah error jika UI belum sepenuhnya dimuat

        # Gambar kotak ROI untuk visualisasi
        cv2.rectangle(frame, (roi_x, roi_y), (roi_x + roi_size, roi_y + roi_size), (0, 255, 0), 2)
        return frame

    def add_data_point(self):
        """Menambahkan titik data baru untuk kalibrasi ulang."""
        try:
            lux_from_meter = float(self.ids.lux_meter_input.text)
            pixel_value = self.current_max_val
            self.calibration_data.append((pixel_value, lux_from_meter))
            
            log_entry = f"Data-{len(self.calibration_data)}: (Piksel: {pixel_value}, Lux: {lux_from_meter})\n"
            self.ids.data_log.text += log_entry
            toast(f"Data ke-{len(self.calibration_data)} ditambahkan.")
            self.ids.lux_meter_input.text = ""
        except ValueError:
            toast("Input dari Luxmeter harus berupa angka!")
        except Exception as e:
            toast(f"Error: {e}")

    def clear_data(self):
        """Membersihkan data kalibrasi yang sudah diinput."""
        self.calibration_data = []
        try:
            self.ids.data_log.text = ""
            self.ids.lux_meter_input.text = ""
            self.ids.result_slope.text = "Hasil Slope: -"
            self.ids.result_intercept.text = "Hasil Intercept: -"
            toast("Data dibersihkan.")
        except KeyError:
            pass

    def calculate_and_save(self):
        if len(self.calibration_data) < 2:
            toast("Data tidak cukup! Kumpulkan minimal 2 titik data.")
            return

        try:
            x_values = np.array([item[0] for item in self.calibration_data])
            y_values = np.array([item[1] for item in self.calibration_data])
            slope, intercept = np.polyfit(x_values, y_values, 1)

            # Buat objek ConfigParser BARU untuk memastikan tidak ada data lama
            local_config = configparser.ConfigParser()
            local_config.read(config_full_path) # Baca seluruh isi file yang ada

            if not local_config.has_section('camera_calibration'):
                local_config.add_section('camera_calibration')
            
            # Atur nilai baru
            local_config.set('camera_calibration', 'intensity_slope', str(slope))
            local_config.set('camera_calibration', 'intensity_intercept', str(intercept))
            current_exposure = self.ids.exposure_slider.value
            local_config.set('camera_calibration', 'exposure', str(current_exposure))

            # Tulis kembali seluruh konfigurasi ke file
            with open(config_full_path, 'w') as configfile:
                local_config.write(configfile)
            
            # Perbarui nilai internal dan UI
            self.INTENSITY_SLOPE = slope
            self.INTENSITY_INTERCEPT = intercept
            self.ids.result_slope.text = f"Hasil Slope: [b]{slope:.4f}[/b]"
            self.ids.result_intercept.text = f"Hasil Intercept: [b]{intercept:.4f}[/b]"
            
            toast("Kalibrasi baru berhasil disimpan!", duration=3)

        except PermissionError:
            toast("Gagal menyimpan: Izin ditolak. Coba jalankan sebagai administrator.")
        except Exception as e:
            toast(f"Gagal menghitung atau menyimpan: {e}")
            Logger.error(f"{self.name}: Gagal kalkulasi/simpan - {e}")

    def exec_navigate_main(self):
        """Fungsi untuk kembali ke menu utama."""
        self.manager.current = 'screen_main'

class RootScreen(ScreenManager):
    pass             

class HeadSoundWindowMeterApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_resize=self.on_window_resize)

    def build(self):
        global window_size_x, window_size_y
        self.theme_cls.colors = colors
        self.theme_cls.primary_palette = "Gray"
        self.theme_cls.accent_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.icon = 'assets/images/logo-load-app.png'
        window_size_y = Window.size[0]
        window_size_x = Window.size[1]
        self.set_dynamic_fonts(Window.size)

        LabelBase.register(
            name="Orbitron-Regular",
            fn_regular="assets/fonts/Orbitron-Regular.ttf")
        
        LabelBase.register(
            name="Draco",
            fn_regular="assets/fonts/Draco.otf")        

        LabelBase.register(
            name="Recharge",
            fn_regular="assets/fonts/Recharge.otf") 
        
        theme_font_styles.append('H1')
        self.theme_cls.font_styles["H1"] = [
            "Orbitron-Regular", 64, False, 0.15]       

        theme_font_styles.append('H2')
        self.theme_cls.font_styles["H2"] = [
            "Orbitron-Regular", 32, False, 0.15] 
        
        theme_font_styles.append('H4')
        self.theme_cls.font_styles["H4"] = [
            "Recharge", 30, False, 0.15] 

        theme_font_styles.append('H5')
        self.theme_cls.font_styles["H5"] = [
            "Recharge", 20, False, 0.15] 

        theme_font_styles.append('H6')
        self.theme_cls.font_styles["H6"] = [
            "Recharge", 16, False, 0.15] 

        theme_font_styles.append('Subtitle1')
        self.theme_cls.font_styles["Subtitle1"] = [
            "Recharge", 11, False, 0.15] 

        theme_font_styles.append('Body1')
        self.theme_cls.font_styles["Body1"] = [
            "Recharge", 10, False, 0.15] 
        
        theme_font_styles.append('Button')
        self.theme_cls.font_styles["Button"] = [
            "Recharge", 9, False, 0.15] 

        theme_font_styles.append('Caption')
        self.theme_cls.font_styles["Caption"] = [
            "Recharge", 8, False, 0.15]       
        
        Window.fullscreen = 'auto'
        Builder.load_file('main.kv')
        return RootScreen()

    def on_window_resize(self, window, width, height):
        Logger.info(f"Window size: {width}x{height}")
        self.set_dynamic_fonts((width, height))
        self.refresh_all_fonts()

    def refresh_all_fonts(self):
        # Refresh fonts for all screens in the ScreenManager
        if hasattr(self, 'root') and hasattr(self.root, 'screens'):
            for screen in self.root.screens:
                self.refresh_fonts(screen)

    def refresh_fonts(self, widget):
        from kivymd.uix.label import MDLabel
        if isinstance(widget, MDLabel):
            original_style = widget.font_style
            temp_style = "Body1" if original_style != "Body1" else "H6"
            widget.font_style = temp_style
            widget.font_style = original_style
        if hasattr(widget, 'children'):
            for child in widget.children:
                self.refresh_fonts(child)

    def set_dynamic_fonts(self, size):
        try:
            screen_size_x = Window.system_size[0]
            screen_size_y = Window.system_size[1]
        except AttributeError:
            screen_size_x = Window._get_system_size()[0]
            screen_size_y = Window._get_system_size()[1]
        font_size_l = np.array([64, 32, 30, 20, 16, 11, 10, 9, 8])
        scale = min(screen_size_x / 1920, screen_size_y / 1080)
        font_size = np.round(font_size_l * scale, 0)
        Logger.info(f"Font resized: {font_size_l} to {font_size}")
        self.theme_cls.font_styles["H1"] = [
            "Orbitron-Regular", font_size[0], False, 0.15]
        self.theme_cls.font_styles["H2"] = [
            "Orbitron-Regular", font_size[1], False, 0.15]
        self.theme_cls.font_styles["H4"] = [
            "Recharge", font_size[2], False, 0.15]
        self.theme_cls.font_styles["H5"] = [
            "Recharge", font_size[3], False, 0.15]
        self.theme_cls.font_styles["H6"] = [
            "Recharge", font_size[4], False, 0.15]
        self.theme_cls.font_styles["Subtitle1"] = [
            "Recharge", font_size[5], False, 0.15]
        self.theme_cls.font_styles["Body1"] = [
            "Recharge", font_size[6], False, 0.15]
        self.theme_cls.font_styles["Button"] = [
            "Recharge", font_size[7], False, 0.15]
        self.theme_cls.font_styles["Caption"] = [
            "Recharge", font_size[8], False, 0.15]       

        if hasattr(self, 'root'):
            self.refresh_fonts(self.root)

if __name__ == '__main__':
    HeadSoundWindowMeterApp().run()
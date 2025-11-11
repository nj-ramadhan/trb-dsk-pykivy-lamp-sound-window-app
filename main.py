import os
import sys

from kivy.config import Config
Config.set('kivy', 'keyboard_mode', 'system')

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
from kivy.graphics.texture import Texture
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
from attr import s
import serial
from serial.tools import list_ports
import os, sys, time
import ssl
import datetime


colors = {
    "Red"   : {"A200": "#FF2A2A","A500": "#FF8080","A700": "#FFD5D5",},
    "Gray"  : {"200": "#CCCCCC","500": "#ECECEC","700": "#F9F9F9",},
    "Blue"  : {"200": "#4471C4","500": "#5885D8","700": "#6C99EC",},
    "Green" : {"200": "#2CA02C","500": "#2DB97F", "700": "#D5FFD5",},
    "Yellow": {"200": "#ffD42A","500": "#ffE680","700": "#fff6D5",},

    "Light" : {"StatusBar": "E0E0E0","AppBar": "#202020","Background": "#EEEEEE","CardsDialogs": "#FFFFFF","FlatButtonDown": "#CCCCCC",},
    "Dark"  : {"StatusBar": "101010","AppBar": "#E0E0E0","Background": "#111111","CardsDialogs": "#222222","FlatButtonDown": "#DDDDDD",},
}

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

try:
    # 1. Baca data string dari config
    rms_values_str = config['calibration_slm']['rms_values']
    db_values_str = config['calibration_slm']['db_values']

    # 2. Ubah string (dipisah koma) menjadi list angka (float)
    amplitudo_samples = [float(rms) for rms in rms_values_str.split(',')]
    db_samples = [float(db) for db in db_values_str.split(',')]

    # 3. Buat model
    coefficients = np.polyfit(amplitudo_samples, db_samples, 2)
    db_conversion_model = np.poly1d(coefficients)
    
    print("Model kalibrasi SLM berhasil dimuat dari config.ini.")

except Exception as e:
    print(f"ERROR: Gagal memuat kalibrasi dari config.ini: {e}. Menggunakan data default.")
    
    # --- TAMBAHKAN KODE FALLBACK INI ---
    amplitudo_samples = [0.0634, 0.1427, 0.2206, 0.2678, 0.3085, 0.3583, 0.3647, 0.4800]
    db_samples = [61.0, 68.5, 72.7, 75, 80.8, 90.2, 95.8, 128.6]
    coefficients = np.polyfit(amplitudo_samples, db_samples, 2)
    db_conversion_model = np.poly1d(coefficients)

def konversi_ke_db(amplitudo_rms):
    if amplitudo_rms < 0.001:
        return 0.0 
    db_value = db_conversion_model(amplitudo_rms)
    return db_value

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
DB_HOST = "194.31.53.37"
DB_USER = "Pndujikir2022!"
DB_PASSWORD = "@Kirpnd2022!"
DB_NAME = "pkbpandeglang"
# DB_HOST = "156.67.217.60"
# DB_USER = "pkbsorong2024!"
# DB_PASSWORD = "@Sorongpkb2024"
# DB_NAME = "dishub"
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
        global dt_id_user, dt_user, dt_slm_user, dt_wtm_user

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
            global dt_no_antrian, dt_no_pol, dt_no_uji, dt_nama, dt_slm_flag, dt_wtm_flag
            global dt_merk, dt_type, dt_jenis_kendaraan, dt_jbb, dt_bahan_bakar, dt_warna
            global db_antrian, db_merk

            try:
                row = int(str(instance.id).replace("card_antrian",""))
                dt_no_antrian          = f"{db_antrian[0, row]}"
                dt_no_pol              = f"{db_antrian[1, row]}"
                dt_no_uji              = f"{db_antrian[2, row]}"
                # PENTING: Ubah flag menjadi teks yang lebih deskriptif untuk ditampilkan di menu
                dt_slm_flag            = 'Lulus' if (int(db_antrian[3, row]) == 1) else 'Tidak Lulus' if (int(db_antrian[3, row]) == 0) else 'Belum Uji'
                dt_wtm_flag            = 'Lulus' if (int(db_antrian[4, row]) == 1) else 'Tidak Lulus' if (int(db_antrian[4, row]) == 0) else 'Belum Uji'                
                dt_merk                = f"{db_merk[np.where(db_merk == db_antrian[5, row])[0][0],1]}"
                dt_type                = f"{db_antrian[6, row]}"
                dt_jenis_kendaraan     = f"{db_antrian[7, row]}"
                dt_jbb                 = f"{db_antrian[8, row]}"
                dt_bahan_bakar         = f"{db_antrian[9, row]}"
                dt_warna               = f"{db_antrian[10, row]}"
                
                self.manager.current = 'screen_menu' 

            except Exception as e:
                toast_msg = f'Error Execute Command from Table Row: {e}'
                toast(toast_msg)

    def regular_update_display(self, dt):
        global flag_conn_stat
        global count_starting, count_get_data
        global dt_user, dt_no_antrian, dt_no_pol, dt_no_uji, dt_nama, dt_jenis_kendaraan
        global dt_slm_flag, dt_slm_value, dt_slm_user, dt_slm_post
        global dt_wtm_flag, dt_wtm_value, dt_wtm_user, dt_wtm_post
        
        try:
            screen_home = self.screen_manager.get_screen('screen_home')
            screen_login = self.screen_manager.get_screen('screen_login')
            screen_menu = self.screen_manager.get_screen('screen_menu')
            screen_slm = self.screen_manager.get_screen('screen_slm')
            screen_wtm = self.screen_manager.get_screen('screen_wtm')

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
            query_table = f"""
            SELECT
                noantrian, nopol, nouji, slm_flag, wtm_flag,
                merk, type, idjeniskendaraan, jbb, bahan_bakar, warna
            FROM {TB_DATA}
            WHERE   slm_flag = 2 OR wtm_flag = 2"""

            tb_antrian.execute(query_table)
            result_tb_antrian = tb_antrian.fetchall()

            mydb.commit()
            db_antrian = np.array(result_tb_antrian).T
            cursor_belum_uji = mydb.cursor(buffered=True)
            query_belum_uji = f"SELECT COUNT(*) FROM {TB_DATA} WHERE slm_flag = 2 OR wtm_flag = 2"
            cursor_belum_uji.execute(query_belum_uji)
            dt_dash_belum_uji = cursor_belum_uji.fetchone()[0]

            mydb.commit()
            cursor_sudah_uji = mydb.cursor(buffered=True)
            query_sudah_uji = f"SELECT COUNT(*) FROM {TB_DATA} WHERE slm_flag != 2 AND wtm_flag != 2"
            cursor_sudah_uji.execute(query_sudah_uji)
            dt_dash_sudah_uji = cursor_sudah_uji.fetchone()[0]

            mydb.commit()
            dt_dash_pendaftaran = dt_dash_belum_uji + dt_dash_sudah_uji
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
                txt_slm_flag = 'Lulus' if (int(db_antrian[3, i]) == 1) else 'Tidak Lulus' if (int(db_antrian[3, i]) == 0) else 'Belum Uji'
                txt_wtm_flag = 'Lulus' if (int(db_antrian[4, i]) == 1) else 'Tidak Lulus' if (int(db_antrian[4, i]) == 0) else 'Belum Uji'
                layout_list.add_widget(
                    MDCard(
                        MDLabel(text=f"{db_antrian[0, i]}", size_hint_x= 0.05), # noantrian (0)
                        MDLabel(text=f"{db_antrian[1, i]}", size_hint_x= 0.08), # nopol (1)
                        MDLabel(text=f"{db_antrian[2, i]}", size_hint_x= 0.08), # nouji (2)
                        MDLabel(text=txt_slm_flag, size_hint_x= 0.07), # Cek slm_flag (3)
                        MDLabel(text=txt_wtm_flag, size_hint_x= 0.07), # Cek wtm_flag (4)
                        MDLabel(text=f"{db_merk[np.where(db_merk == db_antrian[5, i])[0][0],1]}", size_hint_x= 0.1), # merk (5)
                        MDLabel(text=f"{db_antrian[6, i]}", size_hint_x= 0.08), # type (6)
                        MDLabel(text=f"{db_antrian[7, i]}", size_hint_x= 0.15), # idjeniskendaraan (7)
                        MDLabel(text=f"{db_antrian[8, i]}", size_hint_x= 0.05), # jbb (8)
                        MDLabel(text=f"{db_antrian[9, i]}", size_hint_x= 0.1), # bahan_bakar (9)
                        MDLabel(text=f"{db_antrian[10, i]}", size_hint_x= 0.08), # warna (10)

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
            print(f"DEBUG: Error saat membuat MDCard: {e}")
            print(toast_msg)

    def reset_data(self):
        global db_slm_value, count_starting, count_get_data, dt_slm_value        
        count_starting = COUNT_STARTING
        count_get_data = COUNT_ACQUISITION
        dt_slm_value = 0.0
        db_slm_value = np.array([0.0])


    def regular_get_data_slm(self, dt):
        global flag_play
        global dt_slm_value
        global db_slm_value, count_starting, count_get_data
        try:
            if flag_play:
                
                # --- Fase Countdown ---
                if(count_starting > 0):
                    count_starting -= 1
                    # Baca audio HANYA untuk "membuang" buffer, jangan diproses
                    try:
                        # Kita harus tetap membaca stream agar buffer tidak penuh
                        stream.read(CHUNK, exception_on_overflow=False)
                    except Exception as audio_err_countdown:
                        print(f"Audio reading error during countdown (ignored): {audio_err_countdown}")
                    return # JANGAN proses audio lebih lanjut, masih countdown

                # --- Fase Pengukuran ---
                # (Jika kode sampai sini, artinya count_starting sudah 0)
                if(count_get_data > 0):
                    count_get_data -= 1
                    # Ini adalah fase pengukuran, jadi kita proses audionya
                
                # --- Fase Selesai ---
                elif(count_get_data <= 0):
                    flag_play = False
                    Clock.unschedule(self.regular_get_data_slm)
                    if stream.is_active():
                        stream.stop_stream() # Hentikan stream setelah selesai
                    return # Selesai

                # --- Proses Audio (HANYA JIKA count_starting <= 0) ---
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    numpy_data = np.frombuffer(data, dtype=np.int16)
                    normalized_data = numpy_data / 32768.0
                    rms_amplitude = np.sqrt(np.mean(normalized_data**2))

                    print(f"Amplitudo RMS Mentah: {rms_amplitude:.4f}") # Cetak hanya saat mengukur
                    
                    # KONVERSI DAN AMBIL NILAI MAX
                    sound_level_db = konversi_ke_db(rms_amplitude)
                    dt_slm_value = max(dt_slm_value, sound_level_db) # <-- SEKARANG AMAN

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


    def exec_start_slm(self):
        global flag_play, stream
        if not flag_play:
            try:
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
        global stream, flag_play

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
        try:
            # Jika tidak ada tes yg sedang berjalan DAN stream mati, nyalakan
            if not flag_play and not stream.is_active():
                print("Stream diaktifkan oleh ScreenMenu")
                stream.start_stream()
        except Exception as e:
            toast(f"Error memulai stream di menu: {e}")
            print(f"Error di ScreenMenu.on_enter (stream): {e}")

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
        global stream, flag_pla
        try:
            # Jika tidak ada tes yg berjalan & stream aktif, matikan
            if not flag_play and stream.is_active():
                print("Stream dimatikan oleh ScreenMenu (kembali)")
                stream.stop_stream()
        except Exception as e:
            print(f"Error stop stream di exec_navigate_main: {e}")

        self.manager.current = 'screen_main'
            
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
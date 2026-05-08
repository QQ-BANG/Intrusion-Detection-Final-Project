
import os
from pathlib import Path

# project root is two levels up from this file (src/ids_pipeline/config.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
PROCESSED_DIR = DATA_DIR / 'processed'

OUTPUTS_DIR = PROJECT_ROOT / 'outputs'
FIGURES_DIR = OUTPUTS_DIR / 'figures'
MODELS_DIR = OUTPUTS_DIR / 'models'
REPORTS_DIR = OUTPUTS_DIR / 'reports'

SQL_DIR = PROJECT_ROOT / 'sql'

DB_PATH = PROCESSED_DIR / 'ids.sqlite'
DB_URL = "sqlite:///" + str(DB_PATH)

# NSL-KDD is the clean version of DARPA csv
NSL_KDD_URLS = {
    "KDDTrain+.txt": [
        "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain%2B.txt",
        # backup mirror 
        "https://raw.githubusercontent.com/HoaNP/NSL-KDD-DataSet/master/KDDTrain%2B.txt",
    ],
    "KDDTest+.txt": [
        "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTest%2B.txt",
        "https://raw.githubusercontent.com/HoaNP/NSL-KDD-DataSet/master/KDDTest%2B.txt",
    ],
}

# 41 features and 2 labels
NSL_KDD_COLUMNS = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
    "land", "wrong_fragment", "urgent", "hot", "num_failed_logins",
    "logged_in", "num_compromised", "root_shell", "su_attempted", "num_root",
    "num_file_creations", "num_shells", "num_access_files",
    "num_outbound_cmds", "is_host_login", "is_guest_login", "count",
    "srv_count", "serror_rate", "srv_serror_rate", "rerror_rate",
    "srv_rerror_rate", "same_srv_rate", "diff_srv_rate",
    "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
    "label", "difficulty",
]

CATEGORICAL_COLS = ["protocol_type", "service", "flag"]

#binary cols
BINARY_COLS = ["land", "logged_in", "root_shell", "su_attempted",
               "is_host_login", "is_guest_login"]

# 39 NSL-KDD labels -> 4 DARPA attack families (+ normal)
# I built this from the dataset README + the Tavallaee paper.
ATTACK_FAMILY = {
    "normal": "normal",

    # DoS attacks
    "back": "dos",
    "land": "dos",
    "neptune": "dos",
    "pod": "dos",
    "smurf": "dos",
    "teardrop": "dos",
    "apache2": "dos",
    "udpstorm": "dos",
    "processtable": "dos",
    "worm": "dos",
    "mailbomb": "dos",

    # Probe/scan
    "ipsweep": "probe",
    "nmap": "probe",
    "portsweep": "probe",
    "satan": "probe",
    "mscan": "probe",
    "saint": "probe",

    # remote to local remote to local
    "ftp_write": "r2l",
    "guess_passwd": "r2l",
    "imap": "r2l",
    "multihop": "r2l",
    "phf": "r2l",
    "spy": "r2l",
    "warezclient": "r2l",
    "warezmaster": "r2l",
    "xlock": "r2l",
    "xsnoop": "r2l",
    "snmpguess": "r2l",
    "snmpgetattack": "r2l",
    "httptunnel": "r2l",
    "sendmail": "r2l",
    "named": "r2l",

    # user to root
    "buffer_overflow": "u2r",
    "loadmodule": "u2r",
    "perl": "u2r",
    "rootkit": "u2r",
    "ps": "u2r",
    "sqlattack": "u2r",
    "xterm": "u2r",
}

RANDOM_STATE = 42  

# make sure the output folders exist on import
for d in [RAW_DIR, PROCESSED_DIR, FIGURES_DIR, MODELS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

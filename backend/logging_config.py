"""
Configuración de logging mejorado para el sistema
"""
import logging
import sys
from datetime import datetime

def setup_logging():
    """Configura el sistema de logging con formato detallado"""
    
    # Formato detallado con colores (solo para consola)
    class ColoredFormatter(logging.Formatter):
        """Formatter con colores para la consola"""
        
        COLORS = {
            'DEBUG': '\033[36m',      # Cyan
            'INFO': '\033[32m',       # Verde
            'WARNING': '\033[33m',    # Amarillo
            'ERROR': '\033[31m',      # Rojo
            'CRITICAL': '\033[35m',   # Magenta
            'RESET': '\033[0m'
        }
        
        def format(self, record):
            log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{log_color}{record.levelname:8}{self.COLORS['RESET']}"
            return super().format(record)
    
    # Configurar logger raíz
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Handler para consola con colores
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        '%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # Limpiar handlers existentes y agregar el nuevo
    logger.handlers.clear()
    logger.addHandler(console_handler)
    
    return logger

# Emojis para logs más visuales
EMOJI = {
    'start': '🚀',
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'search': '🔍',
    'database': '💾',
    'document': '📄',
    'money': '💰',
    'user': '👤',
    'check': '✓',
    'cross': '✗',
    'arrow': '→',
    'bullet': '•'
}

def log_section(logger, title):
    """Loguea una sección con separador visual"""
    logger.info("=" * 60)
    logger.info(f"{EMOJI['start']} {title}")
    logger.info("=" * 60)

def log_step(logger, step_number, description):
    """Loguea un paso del proceso"""
    logger.info(f"{EMOJI['arrow']} PASO {step_number}: {description}")

def log_success(logger, message):
    """Loguea un éxito"""
    logger.info(f"{EMOJI['success']} {message}")

def log_error(logger, message):
    """Loguea un error"""
    logger.error(f"{EMOJI['error']} {message}")

def log_warning(logger, message):
    """Loguea un warning"""
    logger.warning(f"{EMOJI['warning']} {message}")

def log_info(logger, message):
    """Loguea información"""
    logger.info(f"{EMOJI['info']} {message}")

def log_database(logger, operation, table, details=""):
    """Loguea operación de base de datos"""
    logger.info(f"{EMOJI['database']} DB {operation}: {table} {details}")

def log_found(logger, entity, value):
    """Loguea cuando se encuentra algo"""
    logger.info(f"{EMOJI['check']} Encontrado {entity}: {value}")

def log_not_found(logger, entity, value):
    """Loguea cuando NO se encuentra algo"""
    logger.warning(f"{EMOJI['cross']} NO encontrado {entity}: {value}")

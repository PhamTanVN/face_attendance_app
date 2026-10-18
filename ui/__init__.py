"""UI package for the face attendance application."""

from ui.home import HomePage
from ui.attendance import AttendancePage
from ui.students import StudentPage
from ui.crud import CrudPage
from ui.statistics import StatisticsPage
from ui.touch_utils import (
    TouchLineEdit, TouchComboBox, InfoDialog, ConfirmDialog, 
    PinDialog, TimeRangeDialog, FaceCaptureDialog
)

__all__ = [
    'HomePage',
    'AttendancePage',
    'StudentPage',
    'CrudPage',
    'StatisticsPage',
    'TouchLineEdit',
    'TouchComboBox',
    'InfoDialog',
    'ConfirmDialog',
    'PinDialog',
    'TimeRangeDialog',
    'FaceCaptureDialog'
]
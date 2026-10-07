from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_admin_login_step = State()
    waiting_for_admin_password_step = State()
    waiting_for_password = State()
    waiting_for_shop_location = State()
    waiting_for_shop_radius = State()
    waiting_for_work_times = State()
    waiting_for_emp_login = State()
    waiting_for_emp_password = State()
    waiting_for_new_admin_login = State()
    waiting_for_new_admin_password = State()

class EmployeeStates(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_phone = State()
    waiting_for_login_username = State()
    waiting_for_login_password = State()
    waiting_for_arrival_qr = State()
    waiting_for_arrival_location = State()
    waiting_for_departure_qr = State()
    waiting_for_departure_location = State()
    waiting_for_absence_reason = State()

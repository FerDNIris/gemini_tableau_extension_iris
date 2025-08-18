from ._anvil_designer import client_codeTemplate
from anvil import *
import anvil.server
from anvil import tableau
# Los tipos de Tableau como Mark y DataTable son parte del módulo anvil.tableau
from trexjacket.api import get_dashboard
dashboard = get_dashboard()

class client_code(client_codeTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self._data = None
    self.summary.visible = False
    dashboard.register_event_handler('selection_changed', self.selection_changed_event_handler)

  def selection_changed_event_handler(self, event):
    user_selections = event.worksheet.get_selected_marks()

    # Guardamos la selección si no está vacía
    if user_selections and len(user_selections) > 0:
        self._data = user_selections
    else:
        # Si el usuario anula la selección, limpiamos los datos guardados
        self._data = None

  def btn_submit_click(self, **event_args):
    """This method is called when the button is clicked"""
    data_to_send = self._data

    # Si el usuario no ha seleccionado datos, obtenemos los datos de TODAS las hojas del dashboard.
    if not data_to_send:
        # Esto proporciona un contexto general del dashboard filtrado.
        Notification("No hay selección. Analizando todas las hojas del dashboard...", timeout=3).show()
        try:
            # El método 'get_summary_data_for_all_worksheets' no existe.
            # La forma correcta es iterar sobre cada hoja de cálculo y recopilar sus datos.
            all_data = {}
            for worksheet in dashboard.worksheets:
                # Obtenemos los datos de cada hoja y los guardamos en un diccionario.
                summary_data = worksheet.get_summary_data()
                if summary_data and summary_data.data:
                    all_data[worksheet.name] = summary_data
            
            data_to_send = all_data
            if not data_to_send:
                Notification("No se encontraron datos en ninguna hoja del dashboard.", style="warning", timeout=5).show()
                return
        except Exception as e:
            Notification(f"Error al obtener datos de las hojas: {e}", style="danger", timeout=5).show()
            return

    # --- Nueva lógica para advertencia de volumen de datos ---
    MAX_ROWS_THRESHOLD = 3000 # Define el umbral máximo de filas
    row_count = 0

    if data_to_send:
        # Usamos "duck typing" para contar las filas según el tipo de datos.
        if isinstance(data_to_send, list):
            # Caso 1: Selección de marcas (get_selected_marks).
            row_count = len(data_to_send)
        elif isinstance(data_to_send, dict):
            # Caso 2: Datos de todas las hojas (get_summary_data_for_all_worksheets).
            for table in data_to_send.values():
                if hasattr(table, 'data') and isinstance(getattr(table, 'data', None), list):
                    row_count += len(table.data)
        elif hasattr(data_to_send, 'data') and isinstance(getattr(data_to_send, 'data', None), list):
            # Caso 3: Datos de una sola hoja (fallback de get_summary_data).
            row_count = len(data_to_send.data)

    if row_count > MAX_ROWS_THRESHOLD:
        warning_message = (
            f"Estás a punto de enviar {row_count} filas de datos. "
            f"Esto puede consumir muchos tokens y afectar el rendimiento o el costo del LLM. "
            f"¿Deseas continuar?"
        )
        # Muestra un cuadro de diálogo de confirmación al usuario
        if not confirm(warning_message, title="Advertencia de Gran Volumen de Datos", buttons=[("Continuar", True), ("Cancelar", False)]):
            Notification("Operación cancelada por el usuario.", timeout=2).show()
            return # Detiene la ejecución si el usuario cancela
    # --- Fin de la nueva lógica ---

    Notification("Procesando, por favor espera...", timeout=2).show()
    dataSummary = anvil.server.call('generateDataSummary', prompt=self.user_question.text, data=data_to_send)
    self.summary.visible = True
    self.summary.text = dataSummary
    self._data = None # Limpiamos la selección después de usarla

  def btn_clear_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.summary.text = ''
    self.user_question.text = ''
    self._data = None
    self.summary.visible = False
    

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

    # Si el usuario no ha seleccionado datos, obtenemos los datos de una hoja de trabajo válida
    if not data_to_send:
        # Seleccionar la primera hoja de trabajo disponible en el dashboard.        
        # list(dashboard.worksheets) devuelve una lista de objetos Worksheet, no de nombres.
        all_worksheets = list(dashboard.worksheets)

        if not all_worksheets:
            Notification("Error: No se encontraron hojas de trabajo en este dashboard.", style="danger", timeout=5).show()
            return

        # Seleccionamos el primer objeto Worksheet directamente de la lista.
        worksheet = all_worksheets[0]
        
        # get_summary_data() obtiene todos los datos de la hoja, respetando los filtros aplicados.
        Notification(f"No hay selección. Analizando la primera hoja encontrada: '{worksheet.name}'...", timeout=3).show()
        data_to_send = worksheet.get_summary_data()

    # --- Nueva lógica para advertencia de volumen de datos ---
    MAX_ROWS_THRESHOLD = 3000 # Define el umbral máximo de filas
    row_count = 0

    if data_to_send:
        # Usamos "duck typing" para evitar errores de importación con los tipos de Tableau.
        # get_selected_marks() devuelve una lista.
        if isinstance(data_to_send, list):
            row_count = len(data_to_send)
        # get_summary_data() devuelve un objeto con un atributo 'data' que es una lista.
        elif hasattr(data_to_send, 'data') and isinstance(getattr(data_to_send, 'data', None), list):
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
    

import logging
import typing

import PySimpleGUI as sg


def get_logger(software_name: str) -> logging.Logger:
    """Get general purpose walkman logger."""

    # See https://github.com/PySimpleGUI/PySimpleGUI/issues/2968
    class WindowLoggerHandler(logging.StreamHandler):
        def __init__(
            self, logger_window: typing.Optional[sg.Output] = None, *args, **kwargs
        ):
            super().__init__(*args, **kwargs)
            self.logger_window = logger_window
            self.buffer = ""
            self.formatter = logging.Formatter()

        def update_output(self):
            try:
                self.logger_window.update(value=self.buffer)
            except AttributeError:
                pass

        def emit(self, log_record: logging.LogRecord):
            formatted_log_record = self.formatter.format(log_record)
            self.buffer = f"{self.buffer}\n{formatted_log_record}".strip()
            self.update_output()

    # WARNINGS and LOGGINGS should be caught by the same handlers.
    logging.captureWarnings(True)

    # Name == py.warnings => to ensure we use the logger where the
    # warnings are send to.
    logger = logging.getLogger("py.warnings")

    log_file_path = f"./.{software_name}.log"

    logger.addHandler(logging.FileHandler(log_file_path, mode="w"))
    logger.setLevel(logging.INFO)

    logger.window_logger_handler = WindowLoggerHandler()
    logger.addHandler(logger.window_logger_handler)

    logger.info(f"Log file is written to {log_file_path}.")

    return logger

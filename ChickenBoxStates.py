from abc import ABC, abstractmethod
import paho.mqtt.client as mqtt
from enum import Enum
from threading import Thread
import toml
import os

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "Touchscreen"))
sys.path.append(os.path.join(os.path.dirname(__file__), "Touchscreen", "Framework"))

from PySide6 import QtCore
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QMainWindow
from Touchscreen.go_nogo import startApp, createTouchscreenWindow
from Framework.SessionConfig import SessionConfig
from Framework.TrainingWindow import MainWindow
from PySide6.QtGui import QColor

import serial

config = toml.load("./config.toml")

class DoorIds(Enum):
    FRONT = 1
    EXIT = 2

def open_door(door_id : DoorIds):
    print("Opening door: " + str(door_id))
    
    if door_id == DoorIds.FRONT:
        door_config = config['chickenbox']['gate1']
    else:
        door_config = config['chickenbox']['gate2']

    #ser = serial.Serial(door_config['device'], door_config['baudrate'], timeout=1)
    #ser.write(door_config['open_command'].encode())
    #ser.close()

def close_door(door_id : DoorIds):
    print("Closing door: " + str(door_id))

    if door_id == DoorIds.FRONT:
        door_config = config['chickenbox']['gate1']
    else:
        door_config = config['chickenbox']['gate2']

    #ser = serial.Serial(door_config['device'], door_config['baudrate'], timeout=1)
    #ser.write(door_config['close_command'].encode())
    #ser.close()

class ChickenBoxManager(QtCore.QObject):
    
    start_experiment_signal = QtCore.Signal(object)

    def __init__(self, app = None):
        super().__init__()
        self.app = app
        self.mainWindow = MainWindow()
        self.mainWindow.setStyleSheet("background-color: black;")
        self.mainWindow.setAutoFillBackground(True)

        self.state = StartState(self)

        self.mqtt_thread = Thread(target = self.start_mqtt_client)
        self.mqtt_thread.start()

        self.start_experiment_signal.connect(self.start_experiment)

        self.mainWindow.showFullScreen()

    def start_mqtt_client(self):
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_message = self.on_message
        
        if self.mqtt_client.connect(config['chickenbox']['mqttserver']['url'], config['chickenbox']['mqttserver']['port'], 60) != 0:
            print("Couldn't connect to the mqtt broker")
            sys.exit(1)

        self.mqtt_client.subscribe("chickenbox")

        self.mqtt_client.loop_forever()

    def on_message(self, client, userdata, message):
        print("Message received: " + message.payload.decode())

        if message.payload.decode() == "chicken_detected_in_box":
            self.chicken_detected_in_box()
            
        if message.payload.decode() == "chicken_exited_box":
            self.chicken_exited_box()

    def chicken_detected_in_box(self):
        self.state.chicken_detected_in_box()
    
    def chicken_exited_box(self):
        self.state.chicken_exited_box()

    def experiment_finished(self):
        print("Experiment finished")
        self.state.experiment_finished()
        
    def start_experiment(self):
        print("Starting experiment")
        trainingWindow = createTouchscreenWindow(self.experiment_finished)
        self.mainWindow.setCentralWidget(trainingWindow)
        
    def __del__(self):
        self.mqtt_client.disconnect()

class ChickenBoxState(ABC):
    def __init__(self, manager):
        self.manager = manager

    @abstractmethod
    def chicken_detected_in_box(self):
        pass
    
    @abstractmethod
    def chicken_exited_box(self):
        pass
    
    @abstractmethod
    def experiment_finished(self):
        pass

class StartState(ChickenBoxState):
    def __init__(self, manager):
        print("Entering start state")
        super().__init__(manager)

    def chicken_detected_in_box(self):
        close_door(DoorIds.FRONT)
        self.manager.state = ExperimentState(self.manager)

    def chicken_exited_box(self):
        pass

    def experiment_finished(self):
        pass

class ExperimentState(ChickenBoxState):
    def __init__(self, manager):
        print("Entering experiment state")
        super().__init__(manager)

        self.manager.start_experiment_signal.emit(None)

    def chicken_detected_in_box(self):
        pass
    
    def chicken_exited_box(self):
        pass

    def experiment_finished(self):
        open_door(DoorIds.EXIT)
        self.manager.state = ResetState(self.manager)

class ResetState(ChickenBoxState):
    def __init__(self, manager):
        print("Entering reset state")
        super().__init__(manager)

    def chicken_detected_in_box(self):
        pass
    
    def chicken_exited_box(self):
        close_door(DoorIds.EXIT)
        open_door(DoorIds.FRONT)
        self.manager.state = StartState(self.manager)

    def experiment_finished(self):
        pass

if __name__ == "__main__":
    app = QApplication([])
    app.quitOnLastWindowClosed = True
    manager = ChickenBoxManager(app)
    app.aboutToQuit.connect(manager.__del__)
    sys.exit(app.exec())
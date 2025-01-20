import paho.mqtt.client as mqtt
import toml

config = toml.load("./config.toml")

if __name__ == "__main__":
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.connect(config['chickenbox']['mqttserver']['url'], config['chickenbox']['mqttserver']['port'], 60)
    mqtt_client.publish("chickenbox", "chicken_detected_in_box")
    #mqtt_client.publish("chickenbox", "chicken_exited_box")
    mqtt_client.disconnect()
    print("Messages sent")
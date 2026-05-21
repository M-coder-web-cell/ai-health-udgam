import json
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')  # Serialize data to JSON
)

def send_message(topic_name, data):
    try:
        
        producer.send(topic_name, value=data)
        producer.flush()
        print(f"Message sent to topic {topic_name}: {data}")
    except Exception as e:
        print(f"Error sending message: {e}")
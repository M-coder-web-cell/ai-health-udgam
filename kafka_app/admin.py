from kafka.admin import KafkaAdminClient, NewTopic

# Connect to Kafka broker
admin_client = KafkaAdminClient(
    bootstrap_servers="localhost:9092",
    client_id="test-admin"
)

try: 
    admin_client.create_topics(new_topics=['user-queries'], validate_only=False)
    print("Topic ['user-queries'] created successfully....")
except Exception as e:
    print(f"Error creating topic: {e}")
finally:
    admin_client.close()
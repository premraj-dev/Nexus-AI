from dispatcher import route_and_execute

test_suite = [
    {"id": "Test A", "query": "Suggest me the best recipe for chicken curry"},
    {"id": "Test B", "query": "Write Python code to find duplicate elements in an integer list"},
    {"id": "Test C", "query": "Which laptop should I buy for college?"},
    {"id": "Test D", "query": "Should I use PostgreSQL or MongoDB for my AI application with 10,000 users?"},
    {"id": "Test E", "query": "Should I migrate my 20-service Python monolith to microservices?"},
    {"id": "Test F", "query": "I need the cheapest database with zero maintenance, 100% uptime, and infinite scale."}
]

if __name__ == "__main__":
    for test in test_suite:
        print(f"\n==================== RUNNING {test['id']} ====================")
        print(f"Query: {test['query']}")
        res = route_and_execute(test['query'])
        print(f"[ROUTER RESULT] Mode: {res['mode']} | Debate Rounds: {res['rounds_run']}")
        print(f"[OUTPUT]:\n{res['output']}\n")

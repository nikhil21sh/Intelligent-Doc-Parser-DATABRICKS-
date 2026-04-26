from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

# 1. Design LangGraph state object
class AgentState(TypedDict):
    query: str
    retrieved_facilities: List[Dict[str, Any]]
    reasoning: Dict[str, Any]
    citations: List[str]
    response: str

# Helper to prevent silent failures between nodes
def validate_state(state: AgentState, required_keys: List[str], node_name: str):
    for key in required_keys:
        if not state.get(key):
            raise ValueError(f"State validation failed in {node_name}: missing or empty '{key}'")

# 2. Build 4 nodes with pass-through dummy logic
def retrieve_node(state: AgentState):
    print("-> Executing Retrieve")
    validate_state(state, ["query"], "retrieve_node")
    return {"retrieved_facilities": [{"name": "Mock Hospital", "capability": ["ICU"]}]}

def reason_node(state: AgentState):
    print("-> Executing Reason")
    validate_state(state, ["retrieved_facilities"], "reason_node")
    return {"reasoning": {"gaps": [], "anomalies": []}}

def synthesize_node(state: AgentState):
    print("-> Executing Synthesize")
    validate_state(state, ["reasoning"], "synthesize_node")
    return {"citations": ["row_id_123"]}

def respond_node(state: AgentState):
    print("-> Executing Respond")
    return {"response": "This is a mock final response based on retrieved data."}

# 3. Build and compile graph
workflow = StateGraph(AgentState)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("reason", reason_node)
workflow.add_node("synthesize", synthesize_node)
workflow.add_node("respond", respond_node)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "reason")
workflow.add_edge("reason", "synthesize")
workflow.add_edge("synthesize", "respond")
workflow.add_edge("respond", END)

graph = workflow.compile()

# Test block required by the brief
if __name__ == "__main__":
    print("Testing LangGraph Skeleton...")
    result = graph.invoke({"query": "Find facilities with ICU in Ashanti"})
    print("\nFinal State Reached Successfully!")
    print(result)
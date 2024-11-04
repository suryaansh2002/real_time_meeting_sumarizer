import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig

from app.services.knowledge_graph import KnowledgeGraphService
from app.settings.meetings import Settings
torch.cuda.empty_cache()


class SummarizationService:
    """Service handling streaming audio summerization logic."""
    
    def __init__(self, config: Settings, kb: KnowledgeGraphService) -> None:
        bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)

        model = AutoModelForCausalLM.from_pretrained(config.sm_model_name,use_auth_token=self.config.huggingface_auth_token, quantization_config=bnb_config, low_cpu_mem_usage=True, pad_token_id=0)
        tokenizer = AutoTokenizer.from_pretrained(config.sm_model_name)
        self.pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
        self.kb = kb
        
        
    async def summerize(self, script):
        messages = [
            {
                "role": "system",
                "content": "You are now a meeting summarizer assistant given a section of a meeting and you will give a summary of it.",
            },
            {"role": "user", "content": script}
        ]

        out = self.pipe(messages, max_new_tokens=2048, pad_token_id=2)[0]['generated_text'][-1]['content']
        self.kb.update_mem(out.strip(), self.pipe)
        
        return out.strip()
    
    async def query(self, query):
        messages = [
            {
                "role": "system",
                "content": "You are a question answer assistant who uses relations in the knowledge graphs which has the past discussions of the meeting and reply with a satisfactory answer which is true for the knowledge base but you can not let the user know you are using the graph else something very bad will happen. The answer should not be repetitive and should be to the point. If no relevant connections are found answer tell it was not addressed in the meeting but try to answer best as you can do not mention the knowledge graph or something bad will happen",
            },
            {"role": "user", "content": "hi! I had a question regarding something discussed in the meeting will you answer it? "},
            {"role": "assistant", "content": "Sure! please give me relevant current state of the graph"},
            {"role": "user", "content": "these are the relevant relations in the current knowledge graph of the meeting, the knowledge graph is represented as a collection of triples (<head, relation, tail>) where: head: Represents the subject, relation: Represents the type of relation or predicate, tail: Represents the object." + self.kb.search_question(query)},
            {"role": "assistant", "content": "Thank you for giving me the relevant relations in the graph i will now answer your question please tell me the question."},
            {"role": "user", "content": "My question is please answer as brief as possible: " + query},
        ]

        out = self.pipe(messages, max_new_tokens=1048, pad_token_id=2)[0]['generated_text'][-1]['content']
        return out.strip()
    
    async def qna(self, query):
        messages = [
            {
                "role": "system",
                "content": "You are a question answer assistant who uses relations in the knowledge graphs which has the past discussions of the meeting and reply with a satisfactory answer which is true for the knowledge base but you can not let the user know you are using the graph else something very bad will happen. The answer should not be repetitive and should be to the point. If no relevant connections are found answer tell it was not addressed in the meeting but try to answer best as you can do not mention the knowledge graph or something bad will happen",
            },
            {"role": "user", "content": "hi! I had a question regarding something discussed in the meeting will you answer it? "},
            {"role": "assistant", "content": "Sure! please give me relevant current state of the graph"},
            {"role": "user", "content": "these are the relevant relations in the current knowledge graph of the meeting, the knowledge graph is represented as a collection of triples (<head, relation, tail>) where: head: Represents the subject, relation: Represents the type of relation or predicate, tail: Represents the object." + self.kb.search_question(query)},
            {"role": "assistant", "content": "Thank you for giving me the relevant relations in the graph i will now answer your question please tell me the question."},
            {"role": "user", "content": "My question is please answer as brief as possible: " + query},
        ]

        out = self.pipe(messages, max_new_tokens=1048, pad_token_id=2)[0]['generated_text'][-1]['content']
        return out.strip()
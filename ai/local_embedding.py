from chromadb.utils import embedding_functions
from program_tool import *
import pandas as pd
# from chunking import *

from ai.chunking import *

import chromadb
from chromadb.config import Settings
import json
from openai import OpenAI
from dotenv import load_dotenv


class LocalChromaDB:
    def __init__(self) -> None:
        load_dotenv()
        self.client = OpenAI(api_key="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")
        self.model= "text-embedding-3-large"
        
    def make_db(self,tickers):
        for ticker in tickers:
            path1 = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
            path = os.path.join(path1,f"data/{ticker}.json")
            with open(path, 'r', encoding='utf-8') as f:
                cdict = json.load(f)
        
            chunk = chunk_dict_data(cdict)
            vector = []
            for t in chunk:
                res = self.client.embeddings.create(model=self.model,input=t) # type: ignore
                vec = res.data[0].embedding # type: ignore
                vector.append(vec)

            db_path = os.path.abspath(os.path.dirname(__file__))
            db_path = os.path.join(db_path,"/chroma_db")
            Debuger.printc(db_path)
            client = chromadb.PersistentClient(path="./chroma_db")
        
            collection = client.get_or_create_collection(name=f"{ticker}_report")

            collection.add(
                documents=chunk,
                embeddings= vector,
                ids=[f"doc_{i}" for i in range(len(vector))]
            )


    def get_db(self,ticker):
        path1 = os.path.abspath(os.path.dirname(__file__))
        Debuger.printc(path1)
        db_path = os.path.join(path1,"chroma_db")
        Debuger.printc(db_path)
        client = chromadb.PersistentClient(db_path)
        collection = client.get_collection(name=f"{ticker}_report")

        return collection


if __name__ == "__main__":
    tickers = ["004370","097950"]
    db = LocalChromaDB()
    db.make_db(tickers)
    
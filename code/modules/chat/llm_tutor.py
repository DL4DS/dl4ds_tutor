from modules.chat.helpers import get_prompt
from modules.chat.chat_model_loader import ChatModelLoader
from modules.vectorstore.store_manager import VectorStoreManager
from modules.retriever.retriever import Retriever
from modules.chat.langchain.langchain_rag import CustomConversationalRetrievalChain


class LLMTutor:
    def __init__(self, config, user, logger=None):
        """
        Initialize the LLMTutor class.

        Args:
            config (dict): Configuration dictionary.
            user (str): User identifier.
            logger (Logger, optional): Logger instance. Defaults to None.
        """
        self.config = config
        self.llm = self.load_llm()
        self.user = user
        self.logger = logger
        self.vector_db = VectorStoreManager(config, logger=self.logger)
        if self.config["vectorstore"]["embedd_files"]:
            self.vector_db.create_database()
            self.vector_db.save_database()

    def update_llm(self, new_config):
        """
        Update the LLM and VectorStoreManager based on new configuration.

        Args:
            new_config (dict): New configuration dictionary.
        """
        changes = self.get_config_changes(self.config, new_config)
        self.config = new_config

        if "chat_model" in changes:
            self.llm = self.load_llm()  # Reinitialize LLM if chat_model changes

        if "vectorstore" in changes:
            self.vector_db = VectorStoreManager(
                self.config, logger=self.logger
            )  # Reinitialize VectorStoreManager if vectorstore changes
            if self.config["vectorstore"]["embedd_files"]:
                self.vector_db.create_database()
                self.vector_db.save_database()

    def get_config_changes(self, old_config, new_config):
        """
        Get the changes between the old and new configuration.

        Args:
            old_config (dict): Old configuration dictionary.
            new_config (dict): New configuration dictionary.

        Returns:
            dict: Dictionary containing the changes.
        """
        changes = {}
        for key in new_config:
            if old_config.get(key) != new_config[key]:
                changes[key] = (old_config.get(key), new_config[key])
        return changes

    def retrieval_qa_chain(self, llm, qa_prompt, rephrase_prompt, db, memory=None):
        """
        Create a Retrieval QA Chain.

        Args:
            llm (LLM): The language model instance.
            qa_prompt (str): The QA prompt string.
            rephrase_prompt (str): The rephrase prompt string.
            db (VectorStore): The vector store instance.
            memory (Memory, optional): Memory instance. Defaults to None.

        Returns:
            Chain: The retrieval QA chain instance.
        """
        retriever = Retriever(self.config)._return_retriever(db)

        if self.config["llm_params"]["use_history"]:
            qa_chain = CustomConversationalRetrievalChain(
                llm=llm,
                memory=memory,
                retriever=retriever,
                qa_prompt=qa_prompt,
                rephrase_prompt=rephrase_prompt,
            )
        return qa_chain

    def load_llm(self):
        """
        Load the language model.

        Returns:
            LLM: The loaded language model instance.
        """
        chat_model_loader = ChatModelLoader(self.config)
        llm = chat_model_loader.load_chat_model()
        return llm

    def qa_bot(self, memory=None, qa_prompt=None, rephrase_prompt=None):
        """
        Create a QA bot instance.

        Args:
            memory (Memory, optional): Memory instance. Defaults to None.
            qa_prompt (str, optional): QA prompt string. Defaults to None.
            rephrase_prompt (str, optional): Rephrase prompt string. Defaults to None.

        Returns:
            Chain: The QA bot chain instance.
        """
        if qa_prompt is None:
            qa_prompt = get_prompt(self.config, "qa")
        if rephrase_prompt is None:
            rephrase_prompt = get_prompt(self.config, "rephrase")
        db = self.vector_db.load_database()
        # sanity check to see if there are any documents in the database
        if len(db) == 0:
            raise ValueError(
                "No documents in the database. Populate the database first."
            )
        qa = self.retrieval_qa_chain(self.llm, qa_prompt, rephrase_prompt, db, memory)

        return qa

    def final_result(query):
        """
        Get the final result for a given query.

        Args:
            query (str): The query string.

        Returns:
            str: The response string.
        """
        qa_result = qa_bot()
        response = qa_result({"query": query})
        return response



class DataAgent(Agent):
    """Agent for managing and processing data-related tasks."""

    def process(self,   input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process the input data and return a response.

        This method should be overridden by subclasses to implement specific data processing logic.
        """
        if self.context.get("universe") is None and self.context.get("tickers") is None:
            self.logger.error("No universe or tickers found in context. Initializing default universe and data history.")
            return {
                "status": STATUS_ERROR,
                "input": input_data,
                "output": {},
                "message": "No universe or tickers found in context. Please initialize before processing.",
            }
        if self.context.get("universe") and self.context.get("tickers") is None:
            self.context.set("tickers", Universe(self.context.get("universe")).get_tickers())

        if self.context.get("data_history") is None:
            self.context.set("data_history", DataManager().fetch_history_for_tickers(self.context.get("tickers")))
class AdditionalLogic:
    def __init__(self):
        self.farewell_messages = ['goodbye', 'bye', 'see you', 'later']

    def is_farewell(self, user_input):
        """Check if the input is a farewell message."""
        if any(farewell in user_input.lower() for farewell in self.farewell_messages):
            return True
        return False

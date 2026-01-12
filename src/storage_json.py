import json
import os

class StorageJson:
    def __init__(self, filepath="data/nhl_data.json"):
        self.filepath = filepath
        self.ensure_directory()
        self.data = self.load_data()

    def ensure_directory(self):
        """Creates the data directory if it doesn't exist."""
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def load_data(self):
        """Loads existing data from the JSON file."""
        if not os.path.exists(self.filepath):
            return {"matches": {}}  # Dictionary for O(1) lookups by ID
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"matches": {}}

    def save_data(self):
        """Saves current data to the JSON file."""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            print(f"Database pending saved to {self.filepath}")
        except Exception as e:
            print(f"Error saving database: {e}")

    def match_exists(self, match_id):
        """Checks if a match ID already exists in the database."""
        return match_id in self.data["matches"]

    def add_match(self, match_data):
        """Adds or updates a match in the database."""
        match_id = match_data.get('id')
        if not match_id:
            print("Error: Match data missing ID")
            return

        self.data["matches"][match_id] = match_data
        self.save_data()
        print(f"Saved match {match_id}: {match_data.get('home', '?')} vs {match_data.get('away', '?')}")

    def get_all_matches(self):
        """Returns a list of all matches."""
        return list(self.data["matches"].values())

    def get_stats_summary(self):
        """Returns stats about the database size."""
        return {
            "total_matches": len(self.data["matches"]),
            "filepath": self.filepath
        }

if __name__ == "__main__":
    # Simple test
    storage = StorageJson()
    print(f"Database initialized. Matches found: {storage.get_stats_summary()['total_matches']}")

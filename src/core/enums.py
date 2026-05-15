from enum import Enum, auto

class FieldName(Enum):
    """Enumeration of character card fields"""
    NAME = "name"
    DESCRIPTION = "description"
    SCENARIO = "scenario"
    FIRST_MES = "first_mes"
    MES_EXAMPLE = "mes_example"
    PERSONALITY = "personality"

    @property
    def display_name(self) -> str:
        """Return a user-facing label for the field."""
        labels = {
            FieldName.NAME: "Name",
            FieldName.DESCRIPTION: "Description",
            FieldName.PERSONALITY: "Personality",
            FieldName.SCENARIO: "Scenario",
            FieldName.FIRST_MES: "First Message",
            FieldName.MES_EXAMPLE: "Speech Examples",
        }
        return labels[self]

    @property
    def placeholder_text(self) -> str:
        """Return a user-facing placeholder for field input."""
        placeholders = {
            FieldName.NAME: "Enter name or concept...",
            FieldName.DESCRIPTION: "Enter description notes...",
            FieldName.PERSONALITY: "Enter personality direction...",
            FieldName.SCENARIO: "Enter scenario or premise...",
            FieldName.FIRST_MES: "Enter opening-message direction...",
            FieldName.MES_EXAMPLE: "Enter speech-example direction...",
        }
        return placeholders[self]

    @classmethod
    def ui_order(cls) -> list["FieldName"]:
        """Return the default field order for the UI."""
        return [
            cls.NAME,
            cls.DESCRIPTION,
            cls.PERSONALITY,
            cls.SCENARIO,
            cls.FIRST_MES,
            cls.MES_EXAMPLE,
        ]

class CardFormat(Enum):
    """Supported character card formats"""
    JSON = "json"
    PNG = "png"
    
class GenerationMode(Enum):
    """Different generation modes for fields"""
    DIRECT = auto()  # Use input directly without generation
    GENERATE = auto()  # Generate new content
    HYBRID = auto()  # Combine input with generation
    
class PromptTagType(Enum):
    """Types of tags that can be used in prompts"""
    FIELD = "field"  # References another field
    INPUT = "input"  # User input
    CONDITIONAL = "conditional"  # Conditional content
    CHAR = "char"  # Character name placeholder
    USER = "user"  # User name placeholder
    
class SaveMode(Enum):
    """Different modes for saving character data"""
    OVERWRITE = auto()  # Replace existing file
    NEW = auto()  # Create new file
    VERSIONED = auto()  # Create new version
    
class UIMode(Enum):
    """Different UI modes for field editing"""
    COMPACT = auto()  # Normal view
    EXPANDED = auto()  # Expanded/focused view
    READONLY = auto()  # Non-editable view

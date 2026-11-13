"""Replaces personal data in free text with placeholders before it reaches the LLM.

"Maria" becomes "<PERSON_1>". The lookup table stays in this object, in memory,
so code can put the real values back for the human reviewer. The LLM never sees it.

Detection has three layers, because no single one is enough:
1. Presidio's NLP model finds names we have never seen, but it can split a name in two.
2. Known values from our own data, plus national ID formats, which the model misses.
3. assert_clean is a last check in code: if a known value is still in the text, stop.

This reduces the risk but can't remove it. An unusual name that isn't in our data
can still get past layer 1.
"""

from functools import cache

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

ENTITIES = ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "NATIONAL_ID"]

NATIONAL_ID_PATTERNS = [
    Pattern("ethiopia_fin", r"\bET-FIN-\d{4}-\d{4}-\d{2}\b", 0.9),
    Pattern("colombia_cc", r"\bCC \d{1,2}\.\d{3}\.\d{3}\.\d{3}\b", 0.9),
    Pattern("brazil_cpf", r"\bCPF \d{3}\.\d{3}\.\d{3}-\d{2}\b", 0.9),
    Pattern("vietnam_cccd", r"\bCCCD \d{12}\b", 0.9),
]


@cache
def _analyzer() -> AnalyzerEngine:
    """Loading the NLP model takes a few seconds, so do it once."""
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_md"}],
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=configuration).create_engine()
    return AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])


class Pseudonymizer:
    """known_pii maps an entity type to values we already know, like {"PERSON": [...]}."""

    def __init__(self, known_pii: dict[str, list[str]]) -> None:
        self._known_values = [value for values in known_pii.values() for value in values]
        self._recognizers = [
            PatternRecognizer(supported_entity="NATIONAL_ID", patterns=NATIONAL_ID_PATTERNS),
            *(
                PatternRecognizer(supported_entity=entity, deny_list=values)
                for entity, values in known_pii.items()
                if values
            ),
        ]
        self._token_for_value: dict[str, str] = {}
        self._value_for_token: dict[str, str] = {}
        self._counts: dict[str, int] = {}

    def _token(self, entity: str, value: str) -> str:
        """The same value always gets the same placeholder, so the LLM can tell people apart."""
        if value not in self._token_for_value:
            self._counts[entity] = self._counts.get(entity, 0) + 1
            token = f"<{entity}_{self._counts[entity]}>"
            self._token_for_value[value] = token
            self._value_for_token[token] = value
        return self._token_for_value[value]

    def pseudonymize(self, text: str) -> str:
        findings = _analyzer().analyze(
            text=text,
            language="en",
            entities=ENTITIES,
            ad_hoc_recognizers=self._recognizers,
        )
        operators = {
            entity: OperatorConfig("custom", {"lambda": lambda value, e=entity: self._token(e, value)})
            for entity in ENTITIES
        }
        return AnonymizerEngine().anonymize(text=text, analyzer_results=findings, operators=operators).text

    def restore(self, text: str) -> str:
        """Put the real values back. Only use this on output for the human reviewer."""
        return restore_with(self._value_for_token, text)

    def lookup_table(self) -> dict[str, str]:
        """{placeholder: real value}. Store it apart from the check, never send it to the LLM."""
        return dict(self._value_for_token)

    def assert_clean(self, text: str) -> None:
        """Stop if a known value is still in the text.

        The message counts the leaks and doesn't name them, so an error can't
        carry personal data into a log.
        """
        leaks = sum(value in text for value in self._known_values)
        if leaks:
            raise RuntimeError(f"Stopping: {leaks} known personal value(s) still in the text for the LLM.")


def restore_with(lookup_table: dict[str, str], text: str) -> str:
    """Restore placeholders using a saved lookup table, for example in a later review step."""
    # Longest first, so <PERSON_1> can't replace the start of <PERSON_10>.
    for token in sorted(lookup_table, key=len, reverse=True):
        text = text.replace(token, lookup_table[token])
    return text

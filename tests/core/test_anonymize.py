from src.core.guardrails.anonymize import anonymize_text, deanonymize_text


def test_anonymizes_cnpj():
    text, pii_map = anonymize_text("O CNPJ da empresa é 12.345.678/0001-90")
    assert "12.345.678/0001-90" not in text
    assert len(pii_map) == 1


def test_anonymizes_phone_with_formatting():
    text, pii_map = anonymize_text("Me liga no (11) 91234-5678")
    assert "91234-5678" not in text
    assert len(pii_map) == 1


def test_does_not_confuse_cpf_with_phone():
    text, pii_map = anonymize_text("Meu CPF é 123.456.789-00")
    assert len(pii_map) == 1
    assert next(iter(pii_map)).startswith("[PII_CPF_")


def test_anonymizes_all_occurrences_of_repeated_value():
    text, pii_map = anonymize_text(
        "Meu CPF é 123.456.789-00, repito, 123.456.789-00 é meu CPF"
    )
    assert "123.456.789-00" not in text
    assert len(pii_map) == 1


def test_deanonymize_replaces_token_with_generic_label():
    text, pii_map = anonymize_text("Meu CPF é 123.456.789-00")
    token = next(iter(pii_map))
    result = deanonymize_text(f"Confirmado, seu dado {token} foi recebido.", pii_map)
    assert "CPF OMITIDO" in result
    assert "123.456.789-00" not in result

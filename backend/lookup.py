from backend.data_loader import get_data, new_response, to_item


def lookup_digits(query: str, code: str) -> dict:
    """Handles input that is only digits. No AI is used here."""
    data = get_data()

    if not 2 <= len(code) <= 8:
        return new_response("invalid", query, "HSN codes have 2 to 8 digits. Please check the number.")

    # 2 digits = a whole chapter, not one product
    if len(code) == 2:
        if code not in data.chapters:
            return new_response("invalid", query, f"Chapter {code} does not exist. Chapters run from 01 to 99.")
        headings = [to_item(r) for r in data.records if len(r["code"]) == 4 and r["chapter"] == code]
        response = new_response(
            "chapter",
            query,
            f"Chapter {code} covers many products. Enter a 4 to 8 digit code, or describe the product.",
        )
        response["path"] = data.code_path(code)
        response["candidates"] = headings
        return response

    # Exact match
    exact = data.by_code.get(code)
    if exact:
        response = new_response("found", query)
        response["result"] = to_item(exact)
        response["path"] = data.code_path(code)
        response["confidence"] = "exact"
        response["reason"] = "You entered this code directly, so the data was used without AI."
        return response

    # Not exact: fall back to the closest parent code that exists
    for n in range(len(code) - 1, 3, -1):
        parent = data.by_code.get(code[:n])
        if parent:
            response = new_response(
                "found",
                query,
                f"Code {code} was not found exactly. Showing the closest parent code {parent['code']}.",
            )
            response["result"] = to_item(parent)
            response["path"] = data.code_path(parent["code"])
            response["confidence"] = "closest parent"
            response["reason"] = "The full code is not in the data, so its broader parent is shown."
            return response

    return new_response("not_found", query, f"Code {code} is not in the data.")
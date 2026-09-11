"""Gen AI Mortgage Loan Application - Render deployment entrypoint.
Generated from the supplied Colab notebook while preserving the notebook backend and FastAPI website.
"""


# ===== NOTEBOOK CELL 3 =====
# Render/server-safe environment configuration
import os
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()


# ===== NOTEBOOK CELL 4 =====
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY or "missing-key"
)
print("OpenRouter client initialized")


# ===== NOTEBOOK CELL 5 =====
import json
import re
from typing import Dict, Any, List

print("✅ Required libraries imported")

# ===== NOTEBOOK CELL 6 =====
def call_llm(
    prompt,
    model="openrouter/free",
    temperature=0.2
):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": """
You are an AI assistant working in a
mortgage and loan processing system.

Be accurate, structured and concise.
Follow the requested output format exactly.
"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature
        )

        return response.choices[0].message.content

    except Exception as e:
        return {
            "error": str(e)
        }

# ===== NOTEBOOK CELL 7 =====
def extract_json(response):
    """
    Extract JSON safely from an LLM response.
    """

    if isinstance(response, dict):
        return response

    try:
        # Remove markdown code blocks
        cleaned = response.strip()

        cleaned = cleaned.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        ).strip()

        return json.loads(cleaned)

    except Exception as e:

        return {
            "error": "Failed to parse JSON",
            "raw_response": response,
            "details": str(e)
        }

# ===== NOTEBOOK CELL 8 =====
LENDER_POLICY = {

    "product_name": "STANDARD_HOME_LOAN",

    "age_policy": {
        "minimum_age": 18,

        "maximum_age_at_maturity": {
            "SALARIED": 60,
            "SELF_EMPLOYED": 65
        }
    },

    "income_policy": {
        "minimum_monthly_income": 30000,

        "minimum_work_experience_years": {
            "SALARIED": 2,
            "SELF_EMPLOYED": 3
        }
    },

    "foir_policy": {
        "low_income_max_foir": 40,
        "medium_income_max_foir": 50,
        "high_income_max_foir": 60
    },

    "credit_policy": {
        "preferred_credit_score": 750,
        "minimum_credit_score_for_auto_review": 650
    },

    "required_documents": {

        "ALL_APPLICANTS": [
            "LOAN_APPLICATION",
            "PAN_CARD",
            "IDENTITY_PROOF",
            "ADDRESS_PROOF"
        ],

        "SALARIED": [
            "SALARY_SLIP",
            "BANK_STATEMENT",
            "INCOME_TAX_DOCUMENT"
        ],

        "SELF_EMPLOYED": [
            "ITR",
            "BANK_STATEMENT",
            "BUSINESS_FINANCIALS",
            "BUSINESS_PROOF"
        ],

        "PROPERTY": [
            "PROPERTY_TITLE_DOCUMENT",
            "SALE_AGREEMENT_OR_SALE_DEED",
            "PROPERTY_APPROVAL_DOCUMENT",
            "VALUATION_REPORT"
        ]
    }
}

print("✅ Lender Policy Loaded Successfully")

# ===== NOTEBOOK CELL 9 =====
class BaseAgent:

    def __init__(self, name):
        self.name = name

    def log(self, state, status, message):

        log_entry = {
            "agent": self.name,
            "status": status,
            "message": message
        }

        state["agent_logs"].append(log_entry)

        print(f"[{status}] 🤖 {self.name}: {message}")

        return state

# ===== NOTEBOOK CELL 10 =====
DOCUMENT_TYPES = [
    "LOAN_APPLICATION",

    # KYC
    "PAN_CARD",
    "AADHAAR_CARD",
    "PASSPORT",
    "DRIVING_LICENSE",
    "VOTER_ID",

    # Income - Salaried
    "SALARY_SLIP",
    "BANK_STATEMENT",
    "FORM_16",

    # Income - Self Employed
    "ITR",
    "GST_RETURN",
    "PROFIT_AND_LOSS_STATEMENT",
    "BALANCE_SHEET",
    "BUSINESS_PROOF",

    # Credit
    "CREDIT_REPORT",

    # Property
    "SALE_DEED",
    "SALE_AGREEMENT",
    "PROPERTY_TITLE_DOCUMENT",
    "ENCUMBRANCE_CERTIFICATE",
    "PROPERTY_APPROVAL_DOCUMENT",
    "PROPERTY_TAX_RECEIPT",
    "VALUATION_REPORT",

    # Fallback
    "OTHER"
]

print("✅ Supported document types loaded")
print(f"Total document types: {len(DOCUMENT_TYPES)}")

# ===== NOTEBOOK CELL 11 =====
# ========================================
# AGENT 1
# DOCUMENT INTAKE & CLASSIFICATION AGENT
# ========================================

class DocumentIntakeAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            "Document Intake & Classification Agent"
        )


    def run(self, state):

        self.log(
            state,
            "PROCESSING",
            "Starting document classification"
        )


        # ========================================
        # ENSURE DOCUMENT INVENTORY EXISTS
        # AND IS ALWAYS A DICTIONARY
        # ========================================

        document_inventory = state.get(
            "document_inventory"
        )


        if not isinstance(
            document_inventory,
            dict
        ):

            state["document_inventory"] = {

                "submitted": [],

                "required": [],

                "missing": [],

                "satisfied": [],

                "status": "NOT_PROCESSED"
            }


        # ========================================
        # GET DOCUMENTS SAFELY
        # ========================================

        documents = state.get(
            "documents",
            []
        )


        # ========================================
        # HANDLE NO DOCUMENTS
        # PIPELINE MUST NOT FAIL
        # ========================================

        if not documents:

            state["document_inventory"][
                "submitted"
            ] = []


            state["document_inventory"][
                "status"
            ] = "NO_DOCUMENTS_SUBMITTED"


            self.log(
                state,
                "WARNING",
                "No documents uploaded. "
                "Skipping document classification."
            )


            return state


        # ========================================
        # CLASSIFY DOCUMENTS
        # ========================================

        classified_documents = []


        for document in documents:


            # Skip invalid document objects
            if not isinstance(
                document,
                dict
            ):

                self.log(
                    state,
                    "WARNING",
                    "Invalid document skipped"
                )

                continue


            document_id = document.get(
                "document_id",
                "UNKNOWN"
            )


            document_name = document.get(
                "file_name",
                "UNKNOWN"
            )


            document_content = document.get(
                "content",
                ""
            )


            # ========================================
            # DOCUMENT CLASSIFICATION PROMPT
            # ========================================

            prompt = f"""
You are a Document Classification Agent
for an Indian Home Loan Processing System.

Classify the following document into exactly ONE
of these categories:

{json.dumps(DOCUMENT_TYPES, indent=2)}

DOCUMENT NAME:
{document_name}

DOCUMENT CONTENT:
{document_content}

Return ONLY valid JSON.

Use exactly this structure:

{{
    "document_id": "{document_id}",
    "document_type": "ONE_VALUE_FROM_ALLOWED_TYPES",
    "confidence": 0.0,
    "classification_status": "CLASSIFIED_OR_REVIEW_REQUIRED",
    "reason": "brief explanation"
}}

Rules:

1. Select only one document type from the allowed list.
2. Do not invent information.
3. If classification is uncertain, use OTHER.
4. Confidence must be between 0 and 1.
5. If confidence is below 0.70, set
   classification_status to REVIEW_REQUIRED.
6. Otherwise set classification_status to CLASSIFIED.
7. Return ONLY JSON.
"""


            # ========================================
            # CALL LLM SAFELY
            # ========================================

            try:

                response = call_llm(
                    prompt
                )


                result = extract_json(
                    response
                )


                # Ensure result is valid
                if not isinstance(
                    result,
                    dict
                ):

                    raise ValueError(
                        "Invalid classification result"
                    )


                # ========================================
                # ADD ORIGINAL FILE INFORMATION
                # ========================================

                result[
                    "document_id"
                ] = document_id


                result[
                    "file_name"
                ] = document_name


                result[
                    "file_path"
                ] = document.get(
                    "file_path"
                )


                classified_documents.append(
                    result
                )


            except Exception as e:

                self.log(
                    state,
                    "WARNING",
                    f"Document classification failed "
                    f"for {document_name}: {str(e)}"
                )


                # Add document for review instead
                classified_documents.append({

                    "document_id":
                        document_id,

                    "file_name":
                        document_name,

                    "file_path":
                        document.get(
                            "file_path"
                        ),

                    "document_type":
                        "OTHER",

                    "confidence":
                        0.0,

                    "classification_status":
                        "REVIEW_REQUIRED",

                    "reason":
                        "Document classification failed"
                })


        # ========================================
        # SAVE CLASSIFIED DOCUMENTS
        # ========================================

        state["document_inventory"][
            "submitted"
        ] = classified_documents


        # ========================================
        # UPDATE STATUS
        # ========================================

        if len(classified_documents) == 0:

            state["document_inventory"][
                "status"
            ] = "NO_VALID_DOCUMENTS"


        elif all(

            doc.get(
                "classification_status"
            ) == "CLASSIFIED"

            for doc in classified_documents

        ):

            state["document_inventory"][
                "status"
            ] = "CLASSIFICATION_COMPLETE"


        else:

            state["document_inventory"][
                "status"
            ] = "CLASSIFICATION_PARTIAL"


        # ========================================
        # LOG COMPLETION
        # ========================================

        self.log(
            state,
            "COMPLETED",
            f"Processed {len(documents)} documents. "
            f"Classified {len(classified_documents)} documents."
        )


        return state


print(
    "✅ DocumentIntakeAgent loaded"
)

# ===== NOTEBOOK CELL 12 =====
DOCUMENT_REQUIREMENT_MAPPING = {

    "LOAN_APPLICATION": [
        "LOAN_APPLICATION"
    ],

    "PAN_CARD": [
        "PAN_CARD"
    ],

    "IDENTITY_PROOF": [
        "AADHAAR_CARD",
        "PASSPORT",
        "DRIVING_LICENSE",
        "VOTER_ID"
    ],

    "ADDRESS_PROOF": [
        "AADHAAR_CARD",
        "PASSPORT",
        "DRIVING_LICENSE",
        "VOTER_ID",
        "PROPERTY_TAX_RECEIPT"
    ],

    "SALARY_SLIP": [
        "SALARY_SLIP"
    ],

    "BANK_STATEMENT": [
        "BANK_STATEMENT"
    ],

    "INCOME_TAX_DOCUMENT": [
        "FORM_16",
        "ITR"
    ],

    "ITR": [
        "ITR"
    ],

    "BUSINESS_FINANCIALS": [
        "PROFIT_AND_LOSS_STATEMENT",
        "BALANCE_SHEET"
    ],

    "BUSINESS_PROOF": [
        "GST_RETURN",
        "BUSINESS_PROOF"
    ],

    "PROPERTY_TITLE_DOCUMENT": [
        "PROPERTY_TITLE_DOCUMENT",
        "SALE_DEED"
    ],

    "SALE_AGREEMENT_OR_SALE_DEED": [
        "SALE_AGREEMENT",
        "SALE_DEED"
    ],

    "PROPERTY_APPROVAL_DOCUMENT": [
        "PROPERTY_APPROVAL_DOCUMENT"
    ],

    "VALUATION_REPORT": [
        "VALUATION_REPORT"
    ]
}

print("✅ Document requirement mapping loaded")

# ===== NOTEBOOK CELL 13 =====
# ========================================
# AGENT 2
# DOCUMENT CHECKLIST & MISSING DOCUMENT AGENT
# ========================================

class DocumentChecklistAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            "Document Checklist & Missing Document Agent"
        )


    def run(self, state):

        self.log(
            state,
            "PROCESSING",
            "Determining required documents"
        )


        # ========================================
        # SAFELY GET APPLICANT
        # ========================================

        applicants = state.get(
            "applicants",
            []
        )

        if not applicants:

            self.log(
                state,
                "WARNING",
                "No applicant data available"
            )

            return state


        applicant = applicants[0]


        # ========================================
        # GET EMPLOYMENT TYPE
        # ========================================

        employment_type = (
            applicant.get(
                "employment",
                {}
            ).get(
                "employment_type"
            )
        )


        # ========================================
        # BUILD REQUIRED DOCUMENT LIST
        # ========================================

        required_documents = []


        required_documents.extend(
            LENDER_POLICY
            .get(
                "required_documents",
                {}
            )
            .get(
                "ALL_APPLICANTS",
                []
            )
        )


        if employment_type:

            required_documents.extend(
                LENDER_POLICY
                .get(
                    "required_documents",
                    {}
                )
                .get(
                    employment_type,
                    []
                )
            )


        required_documents.extend(
            LENDER_POLICY
            .get(
                "required_documents",
                {}
            )
            .get(
                "PROPERTY",
                []
            )
        )


        # Remove duplicates
        required_documents = list(
            dict.fromkeys(
                required_documents
            )
        )


        # ========================================
        # ENSURE DOCUMENT INVENTORY IS DICTIONARY
        # ========================================

        document_inventory = state.get(
            "document_inventory",
            {}
        )


        # Fix if previous state accidentally
        # contains a list
        if not isinstance(
            document_inventory,
            dict
        ):

            document_inventory = {
                "submitted": (
                    document_inventory
                    if isinstance(
                        document_inventory,
                        list
                    )
                    else []
                ),
                "required": [],
                "missing": [],
                "satisfied": []
            }


        # Ensure submitted exists
        submitted_documents = (
            document_inventory.get(
                "submitted",
                []
            )
        )


        if not isinstance(
            submitted_documents,
            list
        ):

            submitted_documents = []


        # ========================================
        # GET SUBMITTED DOCUMENT TYPES
        # ========================================

        submitted_types = []


        for doc in submitted_documents:

            if not isinstance(
                doc,
                dict
            ):
                continue


            if (
                doc.get(
                    "classification_status"
                )
                == "CLASSIFIED"
            ):

                document_type = doc.get(
                    "document_type"
                )

                if document_type:

                    submitted_types.append(
                        document_type
                    )


        # ========================================
        # CHECK REQUIREMENTS
        # ========================================

        satisfied_requirements = []

        missing_requirements = []


        for requirement in required_documents:


            accepted_document_types = (
                DOCUMENT_REQUIREMENT_MAPPING
                .get(
                    requirement,
                    [requirement]
                )
            )


            is_satisfied = any(

                document_type
                in submitted_types

                for document_type
                in accepted_document_types

            )


            if is_satisfied:

                satisfied_requirements.append(
                    requirement
                )

            else:

                missing_requirements.append(
                    requirement
                )


        # ========================================
        # SAVE NORMALIZED INVENTORY
        # ========================================

        state[
            "document_inventory"
        ] = {

            "submitted":
                submitted_documents,

            "required":
                required_documents,

            "missing":
                missing_requirements,

            "satisfied":
                satisfied_requirements

        }


        # ========================================
        # LOG RESULT
        # ========================================

        if not submitted_documents:

            self.log(
                state,
                "WARNING",
                f"No documents uploaded. "
                f"{len(missing_requirements)} "
                f"requirements are currently missing."
            )

        else:

            self.log(
                state,
                "COMPLETED",
                f"{len(satisfied_requirements)} "
                f"requirements satisfied, "
                f"{len(missing_requirements)} "
                f"documents/requirements missing"
            )


        return state


print(
    "✅ DocumentChecklistAgent loaded"
)

# ===== NOTEBOOK CELL 14 =====
DOCUMENT_EXTRACTION_SCHEMAS = {

    "PAN_CARD": {
        "full_name": None,
        "date_of_birth": None,
        "pan_number": None
    },

    "AADHAAR_CARD": {
        "full_name": None,
        "date_of_birth": None,
        "address": None
    },

    "PASSPORT": {
        "full_name": None,
        "date_of_birth": None,
        "passport_number": None,
        "address": None,
        "expiry_date": None
    },

    "DRIVING_LICENSE": {
        "full_name": None,
        "date_of_birth": None,
        "license_number": None,
        "address": None,
        "expiry_date": None
    },

    "VOTER_ID": {
        "full_name": None,
        "voter_id_number": None,
        "address": None
    },

    "SALARY_SLIP": {
        "employee_name": None,
        "employee_id": None,
        "employer_name": None,
        "salary_month": None,
        "basic_salary": None,
        "hra": None,
        "allowances": None,
        "gross_salary": None,
        "total_deductions": None,
        "net_salary": None
    },

    "BANK_STATEMENT": {
        "account_holder_name": None,
        "bank_name": None,
        "account_last_4_digits": None,
        "statement_period": None,
        "average_monthly_salary_credit": None,
        "average_monthly_credit": None,
        "existing_monthly_emi": None,
        "returned_or_failed_payments": None
    },

    "FORM_16": {
        "employee_name": None,
        "employer_name": None,
        "financial_year": None,
        "gross_salary": None,
        "taxable_income": None
    },

    "ITR": {
        "taxpayer_name": None,
        "pan_number": None,
        "assessment_year": None,
        "gross_total_income": None,
        "total_income": None
    },

    "CREDIT_REPORT": {
        "consumer_name": None,
        "credit_score": None,
        "total_active_accounts": None,
        "total_outstanding": None,
        "monthly_emi": None,
        "overdue_amount": None,
        "recent_delinquencies": None
    },

    "SALE_DEED": {
        "buyer_name": None,
        "seller_name": None,
        "property_address": None,
        "property_type": None,
        "consideration_value": None,
        "registration_date": None
    },

    "SALE_AGREEMENT": {
        "buyer_name": None,
        "seller_name": None,
        "property_address": None,
        "property_type": None,
        "agreed_property_value": None,
        "agreement_date": None
    },

    "PROPERTY_TITLE_DOCUMENT": {
        "owner_name": None,
        "property_address": None,
        "document_reference_number": None,
        "registration_date": None
    },

    "ENCUMBRANCE_CERTIFICATE": {
        "property_address": None,
        "encumbrance_status": None,
        "certificate_period": None,
        "registered_transactions": None
    },

    "VALUATION_REPORT": {
        "property_address": None,
        "valuer_name": None,
        "valuation_date": None,
        "market_value": None,
        "forced_sale_value": None
    }
}

print("✅ Document extraction schemas loaded")
print(f"Supported extraction schemas: {len(DOCUMENT_EXTRACTION_SCHEMAS)}")

# ===== NOTEBOOK CELL 15 =====
# ========================================
# AGENT 3
# DOCUMENT INTELLIGENCE & DATA EXTRACTION
# ========================================


class DocumentIntelligenceAgent(BaseAgent):


    def __init__(self):

        super().__init__(
            "Document Intelligence & Data Extraction Agent"
        )


    def run(self, state):


        # ========================================
        # START LOG
        # ========================================

        self.log(
            state,
            "PROCESSING",
            "Extracting structured information from classified documents"
        )


        # ========================================
        # SAFELY GET DOCUMENT INVENTORY
        # ========================================

        document_inventory = state.get(
            "document_inventory",
            {}
        )


        # Safety in case document_inventory
        # was accidentally initialized as a list
        if not isinstance(
            document_inventory,
            dict
        ):

            document_inventory = {}

            state[
                "document_inventory"
            ] = document_inventory


        classified_documents = (
            document_inventory.get(
                "submitted",
                []
            )
        )


        # ========================================
        # SAFELY GET ORIGINAL DOCUMENTS
        # ========================================

        original_documents_list = state.get(
            "documents",
            []
        )


        # Safety in case documents is None
        # or not a list
        if not isinstance(
            original_documents_list,
            list
        ):

            original_documents_list = []


        original_documents = {

            document.get(
                "document_id"
            ): document

            for document in original_documents_list

            if isinstance(
                document,
                dict
            )

            and document.get(
                "document_id"
            )
        }


        # ========================================
        # HANDLE NO DOCUMENTS
        # ========================================

        if not classified_documents:


            self.log(
                state,
                "WARNING",
                "No classified documents available for extraction"
            )


            state[
                "extracted_data"
            ] = {
                "documents": []
            }


            return state


        # ========================================
        # EXTRACTION RESULTS
        # ========================================

        extraction_results = []


        # ========================================
        # PROCESS EACH CLASSIFIED DOCUMENT
        # ========================================

        for classified_document in classified_documents:


            # Safety check
            if not isinstance(
                classified_document,
                dict
            ):

                continue


            # ----------------------------------------
            # SKIP DOCUMENTS REQUIRING REVIEW
            # ----------------------------------------

            if (

                classified_document.get(
                    "classification_status"
                )

                != "CLASSIFIED"

            ):

                extraction_results.append({

                    "document_id":

                        classified_document.get(
                            "document_id"
                        ),

                    "document_type":

                        classified_document.get(
                            "document_type",
                            "UNKNOWN"
                        ),

                    "extraction_status":

                        "REVIEW_REQUIRED",

                    "extracted_fields":

                        {},

                    "missing_fields":

                        [],

                    "extraction_issues": [

                        "Document classification requires review"

                    ]

                })


                continue


            # ----------------------------------------
            # GET DOCUMENT DETAILS
            # ----------------------------------------

            document_id = (

                classified_document.get(
                    "document_id"
                )

            )


            document_type = (

                classified_document.get(
                    "document_type"
                )

            )


            # ----------------------------------------
            # CHECK SUPPORTED DOCUMENT TYPE
            # ----------------------------------------

            if (

                document_type

                not in

                DOCUMENT_EXTRACTION_SCHEMAS

            ):


                extraction_results.append({

                    "document_id":

                        document_id,

                    "document_type":

                        document_type,

                    "extraction_status":

                        "NOT_SUPPORTED",

                    "extracted_fields":

                        {},

                    "missing_fields":

                        [],

                    "extraction_issues": [

                        "No extraction schema available"

                    ]

                })


                continue


            # ========================================
            # GET ORIGINAL DOCUMENT
            # ========================================

            # First try original documents
            original_document = (

                original_documents.get(
                    document_id,
                    {}
                )

            )


            # If Agent 1 preserves content
            # inside classified_document,
            # use that as fallback
            if not original_document:

                original_document = (
                    classified_document
                )


            document_content = (

                original_document.get(
                    "content",
                    ""
                )

            )


            # ----------------------------------------
            # HANDLE EMPTY DOCUMENT CONTENT
            # ----------------------------------------

            if not document_content:


                schema = (

                    DOCUMENT_EXTRACTION_SCHEMAS[
                        document_type
                    ]

                )


                extraction_results.append({

                    "document_id":

                        document_id,

                    "document_type":

                        document_type,

                    "extraction_status":

                        "REVIEW_REQUIRED",

                    "extracted_fields":

                        {
                            field: None
                            for field
                            in schema.keys()
                        },

                    "missing_fields":

                        list(
                            schema.keys()
                        ),

                    "extraction_issues": [

                        "Document content is empty or unavailable"

                    ]

                })


                continue


            # ========================================
            # GET EXTRACTION SCHEMA
            # ========================================

            schema = (

                DOCUMENT_EXTRACTION_SCHEMAS[
                    document_type
                ]

            )


            # ========================================
            # BUILD EXTRACTION PROMPT
            # ========================================

            prompt = f"""
You are a structured data extraction system
for an Indian Home Loan Processing System.

Your ONLY task is to extract information
from the provided document.

Do not explain anything.
Do not provide safety messages.
Do not answer conversationally.

DOCUMENT TYPE:
{document_type}

DOCUMENT CONTENT:
{document_content}

Extract data using ONLY this schema:

{json.dumps(schema, indent=2)}

IMPORTANT RULES:

1. Return ONLY a valid JSON object.
2. Do not use markdown.
3. Do not use ```json.
4. Do not add explanations.
5. Do not invent values.
6. Use null for unavailable values.
7. Monetary values must be numbers only.
8. Remove ₹, commas and currency symbols.
9. Dates should use YYYY-MM-DD where possible.
10. Preserve names exactly as shown in the document.

Your response MUST follow exactly this structure:

{{
    "document_id": "{document_id}",
    "document_type": "{document_type}",
    "extraction_status": "SUCCESS",
    "extracted_fields": {{
        ...
    }},
    "missing_fields": [],
    "extraction_issues": []
}}
"""


            # ========================================
            # CALL LLM
            # ========================================

            try:

                response = call_llm(
                    prompt
                )


                result = extract_json(
                    response
                )


            except Exception as e:


                result = {

                    "document_id":

                        document_id,

                    "document_type":

                        document_type,

                    "extraction_status":

                        "REVIEW_REQUIRED",

                    "extracted_fields":

                        {
                            field: None
                            for field
                            in schema.keys()
                        },

                    "missing_fields":

                        list(
                            schema.keys()
                        ),

                    "extraction_issues": [

                        f"Document extraction failed: {str(e)}"

                    ]

                }


            # ========================================
            # HANDLE INVALID JSON RESPONSE
            # ========================================

            if (

                not isinstance(
                    result,
                    dict
                )

                or

                result.get(
                    "error"
                )

                == "Failed to parse JSON"

            ):


                result = {

                    "document_id":

                        document_id,

                    "document_type":

                        document_type,

                    "extraction_status":

                        "REVIEW_REQUIRED",

                    "extracted_fields":

                        {
                            field: None
                            for field
                            in schema.keys()
                        },

                    "missing_fields":

                        list(
                            schema.keys()
                        ),

                    "extraction_issues": [

                        "LLM returned an invalid response",

                        f"Raw response: {response}"

                    ]

                }


            # ========================================
            # ENSURE REQUIRED FIELDS EXIST
            # ========================================

            result[
                "document_id"
            ] = document_id


            result[
                "document_type"
            ] = document_type


            if (

                "extracted_fields"

                not in

                result

                or

                not isinstance(
                    result["extracted_fields"],
                    dict
                )

            ):

                result[
                    "extracted_fields"
                ] = {}


            # ========================================
            # DETERMINE MISSING FIELDS
            # ========================================

            extracted_fields = (

                result[
                    "extracted_fields"
                ]

            )


            missing_fields = [

                field

                for field in schema.keys()

                if extracted_fields.get(
                    field
                )

                is None

            ]


            result[
                "missing_fields"
            ] = missing_fields


            if (

                result.get(
                    "extraction_status"
                )

                != "REVIEW_REQUIRED"

            ):

                result[
                    "extraction_status"
                ] = "SUCCESS"


            result.setdefault(
                "extraction_issues",
                []
            )


            extraction_results.append(
                result
            )


        # ========================================
        # SAVE EXTRACTION RESULTS
        # ========================================

        state[
            "extracted_data"
        ] = {

            "documents":

                extraction_results

        }


        # ========================================
        # CALCULATE SUMMARY
        # ========================================

        successful = len([

            doc

            for doc

            in extraction_results

            if doc.get(
                "extraction_status"
            )

            == "SUCCESS"

        ])


        review_required = len([

            doc

            for doc

            in extraction_results

            if doc.get(
                "extraction_status"
            )

            == "REVIEW_REQUIRED"

        ])


        not_supported = len([

            doc

            for doc

            in extraction_results

            if doc.get(
                "extraction_status"
            )

            == "NOT_SUPPORTED"

        ])


        # ========================================
        # COMPLETE LOG
        # ========================================

        self.log(
            state,
            "COMPLETED",
            f"Successfully extracted {successful} documents. "
            f"{review_required} require review. "
            f"{not_supported} are not supported."
        )


        return state


print(
    "✅ DocumentIntelligenceAgent loaded"
)

# ===== NOTEBOOK CELL 16 =====
def get_extracted_document(
    state,
    document_type
):

    documents = (
        state["extracted_data"]
        .get("documents", [])
    )

    for document in documents:

        if (
            document.get("document_type")
            == document_type
        ):
            return document

    return None


# Test it
# Initialize a dummy loan_state for testing purposes
loan_state = {
    "extracted_data": {
        "documents": [
            {
                "document_type": "PAN_CARD",
                "extracted_fields": {
                    "full_name": "John Doe",
                    "date_of_birth": "1990-01-01",
                    "pan_number": "ABCDE1234F"
                }
            },
            {
                "document_type": "AADHAAR_CARD",
                "extracted_fields": {
                    "full_name": "John Doe",
                    "date_of_birth": "1990-01-01",
                    "address": "123 Main St"
                }
            }
        ]
    }
}

pan_document = get_extracted_document(
    loan_state,
    "PAN_CARD"
)

print(
    json.dumps(
        pan_document,
        indent=2
    )
)

# ===== NOTEBOOK CELL 17 =====
def extract_pan_card_deterministic(content):

    result = {
        "full_name": None,
        "date_of_birth": None,
        "pan_number": None
    }

    # Extract PAN number
    pan_match = re.search(
        r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',
        content.upper()
    )

    if pan_match:
        result["pan_number"] = pan_match.group()

    # Extract name
    name_match = re.search(
        r'Name\s*:\s*([A-Za-z ]+)',
        content,
        re.IGNORECASE
    )

    if name_match:
        result["full_name"] = name_match.group(1).strip()

    # Extract Date of Birth
    dob_match = re.search(
        r'(?:Date\s*of\s*Birth|DOB)\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})',
        content,
        re.IGNORECASE
    )

    if dob_match:

        date_value = dob_match.group(1)

        day, month, year = date_value.split("/")

        result["date_of_birth"] = (
            f"{year}-{month}-{day}"
        )

    return result


print("✅ PAN fallback extractor ready")

# ===== NOTEBOOK CELL 18 =====
# ========================================
# VERIFICATION HELPER FUNCTIONS
# UPDATED VERSION
# ========================================


def normalize_text(value):

    if value is None:
        return None

    normalized = str(value).strip()

    if normalized == "":
        return None

    return re.sub(
        r"\s+",
        " ",
        normalized.lower()
    )


def verify_exact_match(values):

    # ----------------------------------------
    # REMOVE NULL / EMPTY VALUES
    # ----------------------------------------

    valid_values = []

    for value in values:

        normalized = normalize_text(value)

        if normalized is not None:

            valid_values.append(value)


    # ----------------------------------------
    # REQUIRE AT LEAST 2 VALUES
    # ----------------------------------------

    if len(valid_values) < 2:

        return {
            "status": "INSUFFICIENT_DATA",
            "values": valid_values
        }


    # ----------------------------------------
    # NORMALIZE VALID VALUES
    # ----------------------------------------

    normalized_values = [

        normalize_text(value)

        for value in valid_values

    ]


    # ----------------------------------------
    # COMPARE
    # ----------------------------------------

    if len(set(normalized_values)) == 1:

        return {
            "status": "MATCH",
            "values": valid_values
        }


    return {
        "status": "MISMATCH",
        "values": valid_values
    }


def verify_numeric_match(
    values,
    tolerance_percentage=5
):

    # ----------------------------------------
    # CLEAN NUMERIC VALUES
    # ----------------------------------------

    valid_values = []

    for value in values:

        # Ignore None
        if value is None:
            continue

        # Ignore empty strings
        if isinstance(value, str):

            value = value.strip()

            if value == "":
                continue

            # Remove commas and currency symbol
            value = (
                value
                .replace(",", "")
                .replace("₹", "")
            )

        try:

            numeric_value = float(value)

            valid_values.append(
                numeric_value
            )

        except (
            ValueError,
            TypeError
        ):

            continue


    # ----------------------------------------
    # REQUIRE AT LEAST 2 VALID VALUES
    # ----------------------------------------

    if len(valid_values) < 2:

        return {
            "status": "INSUFFICIENT_DATA",
            "values": valid_values
        }


    # ----------------------------------------
    # CALCULATE DIFFERENCE
    # ----------------------------------------

    minimum = min(valid_values)

    maximum = max(valid_values)


    # ----------------------------------------
    # HANDLE ZERO VALUES
    # ----------------------------------------

    if minimum == 0:

        # If all values are zero,
        # they are an exact match
        if maximum == 0:

            return {
                "status": "MATCH",
                "values": valid_values,
                "difference_percentage": 0.0
            }

        return {
            "status": "REVIEW_REQUIRED",
            "values": valid_values
        }


    # ----------------------------------------
    # CALCULATE PERCENTAGE DIFFERENCE
    # ----------------------------------------

    difference_percentage = (

        (maximum - minimum)
        / minimum

    ) * 100


    # ----------------------------------------
    # CHECK TOLERANCE
    # ----------------------------------------

    if difference_percentage <= tolerance_percentage:

        return {
            "status": "MATCH",
            "values": valid_values,
            "difference_percentage": round(
                difference_percentage,
                2
            )
        }


    return {
        "status": "MISMATCH",
        "values": valid_values,
        "difference_percentage": round(
            difference_percentage,
            2
        )
    }


print(
    "✅ Updated verification helper functions loaded"
)

# ===== NOTEBOOK CELL 19 =====
# ========================================
# CELL 45 - AGENT 4
# CROSS-DOCUMENT VERIFICATION AGENT
# FINAL STABLE VERSION
# ========================================


class CrossDocumentVerificationAgent(BaseAgent):


    def __init__(self):

        super().__init__(
            "Cross-Document Verification Agent"
        )


    def get_first_available(
        self,
        data,
        field_names
    ):

        if not isinstance(data, dict):
            return None

        for field_name in field_names:

            value = data.get(
                field_name
            )

            if (
                value is not None
                and value != ""
            ):

                return value

        return None


    def run(self, state):


        self.log(
            state,
            "PROCESSING",
            "Comparing application data with extracted documents"
        )


        # ========================================
        # GET APPLICANT
        # ========================================

        applicants = state.get(
            "applicants",
            []
        )

        applicant = (
            applicants[0]
            if applicants
            else {}
        )


        application_personal = (
            applicant.get(
                "personal_details",
                {}
            )
        )


        application_income = (
            applicant.get(
                "income",
                {}
            )
        )


        application_liabilities = (
            applicant.get(
                "liabilities",
                {}
            )
        )


        # ========================================
        # GET EXTRACTED DOCUMENTS
        # ========================================

        pan_doc = get_extracted_document(
            state,
            "PAN_CARD"
        )


        salary_doc = get_extracted_document(
            state,
            "SALARY_SLIP"
        )


        bank_doc = get_extracted_document(
            state,
            "BANK_STATEMENT"
        )


        # ========================================
        # EXTRACT DOCUMENT DATA
        # ========================================

        pan_data = (
            pan_doc.get(
                "extracted_fields",
                {}
            )
            if pan_doc
            else {}
        )


        salary_data = (
            salary_doc.get(
                "extracted_fields",
                {}
            )
            if salary_doc
            else {}
        )


        bank_data = (
            bank_doc.get(
                "extracted_fields",
                {}
            )
            if bank_doc
            else {}
        )


        # ========================================
        # APPLICATION FIELD NORMALIZATION
        # ========================================

        application_gross_income = (
            self.get_first_available(
                application_income,
                [
                    "gross_monthly_income",
                    "gross_income",
                    "monthly_gross_income",
                    "monthly_income",
                    "gross_salary"
                ]
            )
        )


        application_net_income = (
            self.get_first_available(
                application_income,
                [
                    "net_monthly_income",
                    "net_income",
                    "monthly_net_income",
                    "net_salary"
                ]
            )
        )


        application_existing_emi = (
            self.get_first_available(
                application_liabilities,
                [
                    "existing_monthly_emi",
                    "monthly_emi",
                    "existing_emi"
                ]
            )
        )


        # ========================================
        # DOCUMENT FIELD NORMALIZATION
        # ========================================

        salary_gross_income = (
            self.get_first_available(
                salary_data,
                [
                    "gross_salary",
                    "gross_monthly_income",
                    "monthly_gross_income"
                ]
            )
        )


        salary_net_income = (
            self.get_first_available(
                salary_data,
                [
                    "net_salary",
                    "net_monthly_income",
                    "monthly_net_income"
                ]
            )
        )


        bank_salary_credit = (
            self.get_first_available(
                bank_data,
                [
                    "average_monthly_salary_credit",
                    "average_salary_credit",
                    "monthly_salary_credit"
                ]
            )
        )


        bank_existing_emi = (
            self.get_first_available(
                bank_data,
                [
                    "existing_monthly_emi",
                    "existing_emi",
                    "monthly_emi"
                ]
            )
        )


        # ========================================
        # VERIFICATION RESULTS
        # ========================================

        verification_results = {


            # ------------------------------------
            # NAME
            # ------------------------------------

            "name_verification":

                verify_exact_match([

                    application_personal.get(
                        "full_name"
                    ),

                    pan_data.get(
                        "full_name"
                    ),

                    salary_data.get(
                        "employee_name"
                    ),

                    bank_data.get(
                        "account_holder_name"
                    )

                ]),


            # ------------------------------------
            # DATE OF BIRTH
            # ------------------------------------

            "date_of_birth_verification":

                verify_exact_match([

                    application_personal.get(
                        "date_of_birth"
                    ),

                    pan_data.get(
                        "date_of_birth"
                    )

                ]),


            # ------------------------------------
            # PAN
            # ------------------------------------

            "pan_verification":

                verify_exact_match([

                    application_personal.get(
                        "pan"
                    ),

                    pan_data.get(
                        "pan_number"
                    )

                ]),


            # ------------------------------------
            # GROSS INCOME
            # ------------------------------------

            "gross_income_verification":

                verify_numeric_match([

                    application_gross_income,

                    salary_gross_income

                ]),


            # ------------------------------------
            # NET INCOME
            # ------------------------------------

            "net_income_verification":

                verify_numeric_match([

                    application_net_income,

                    salary_net_income,

                    bank_salary_credit

                ]),


            # ------------------------------------
            # EXISTING EMI
            # ------------------------------------

            "existing_emi_verification":

                verify_numeric_match([

                    application_existing_emi,

                    bank_existing_emi

                ])

        }


        # ========================================
        # CALCULATE SUMMARY
        # ========================================

        statuses = [

            result.get(
                "status"
            )

            for result in
            verification_results.values()

        ]


        match_count = statuses.count(
            "MATCH"
        )


        mismatch_count = statuses.count(
            "MISMATCH"
        )


        insufficient_count = statuses.count(
            "INSUFFICIENT_DATA"
        )


        review_required_count = statuses.count(
            "REVIEW_REQUIRED"
        )


        # ========================================
        # DETERMINE OVERALL STATUS
        # ========================================

        if mismatch_count > 0:

            overall_status = (
                "REVIEW_REQUIRED"
            )


        elif review_required_count > 0:

            overall_status = (
                "REVIEW_REQUIRED"
            )


        elif insufficient_count > 0:

            overall_status = (
                "PARTIALLY_VERIFIED"
            )


        else:

            overall_status = (
                "VERIFIED"
            )


        # ========================================
        # ADD SUMMARY
        # ========================================

        verification_results[
            "summary"
        ] = {

            "total_checks":
                len(statuses),

            "matches":
                match_count,

            "mismatches":
                mismatch_count,

            "review_required":
                review_required_count,

            "insufficient_data":
                insufficient_count,

            "overall_status":
                overall_status

        }


        # ========================================
        # SAVE RESULT
        # ========================================

        state[
            "verification_results"
        ] = verification_results


        self.log(
            state,
            "COMPLETED",
            f"{match_count} matches, "
            f"{mismatch_count} mismatches, "
            f"{review_required_count} require review, "
            f"{insufficient_count} with insufficient data"
        )


        return state


print(
    "✅ Final CrossDocumentVerificationAgent loaded"
)

# ===== NOTEBOOK CELL 20 =====
UNDERWRITING_POLICY = {

    "age": {
        "minimum_age": 21,
        "maximum_age_at_maturity": 65
    },

    "income": {
        "minimum_net_monthly_income": 25000
    },

    "foir": {
        "maximum_foir_percentage": 50
    },

    "ltv": {
        "maximum_ltv_percentage": 80
    },

    "loan_amount": {
        "minimum_loan_amount": 500000,
        "maximum_loan_amount": 100000000
    },

    "credit_score": {
        "minimum_score": 700
    }
}

print("✅ Underwriting policy loaded")

print(
    json.dumps(
        UNDERWRITING_POLICY,
        indent=2
    )
)

# ===== NOTEBOOK CELL 21 =====
from datetime import datetime
import math


def calculate_age(date_of_birth):

    dob = datetime.strptime(
        date_of_birth,
        "%Y-%m-%d"
    )

    today = datetime.today()

    age = (
        today.year
        - dob.year
        - (
            (today.month, today.day)
            < (dob.month, dob.day)
        )
    )

    return age


def calculate_emi(
    principal,
    annual_interest_rate,
    tenure_years
):

    monthly_rate = (
        annual_interest_rate
        / 12
        / 100
    )

    months = tenure_years * 12

    if monthly_rate == 0:

        return principal / months

    emi = (
        principal
        * monthly_rate
        * (1 + monthly_rate) ** months
        / (
            (1 + monthly_rate) ** months
            - 1
        )
    )

    return round(emi, 2)


def calculate_max_emi(
    net_monthly_income,
    existing_emi,
    maximum_foir_percentage
):

    maximum_total_obligation = (
        net_monthly_income
        * maximum_foir_percentage
        / 100
    )

    maximum_new_emi = (
        maximum_total_obligation
        - existing_emi
    )

    return max(
        0,
        round(maximum_new_emi, 2)
    )


def calculate_foir(
    net_monthly_income,
    existing_emi,
    proposed_emi
):

    if net_monthly_income <= 0:
        return None

    total_obligations = (
        existing_emi
        + proposed_emi
    )

    foir = (
        total_obligations
        / net_monthly_income
    ) * 100

    return round(
        foir,
        2
    )


def calculate_max_loan_from_emi(
    max_emi,
    annual_interest_rate,
    tenure_years
):

    monthly_rate = (
        annual_interest_rate
        / 12
        / 100
    )

    months = tenure_years * 12

    if monthly_rate == 0:

        return round(
            max_emi * months,
            2
        )

    principal = (
        max_emi
        * (
            (1 + monthly_rate) ** months
            - 1
        )
        / (
            monthly_rate
            * (1 + monthly_rate) ** months
        )
    )

    return round(
        principal,
        2
    )


print("✅ Underwriting calculation helpers loaded")

# ===== NOTEBOOK CELL 22 =====
# ========================================
# AGENT 5
# LOAN ELIGIBILITY & UNDERWRITING AGENT
# GRADIO SAFE VERSION
# ========================================

class LoanEligibilityUnderwritingAgent(BaseAgent):


    def __init__(self):

        super().__init__(
            "Loan Eligibility & Underwriting Agent"
        )


    def run(self, state):


        self.log(
            state,
            "PROCESSING",
            "Evaluating loan eligibility and underwriting rules"
        )


        # ========================================
        # ENSURE REQUIRED STATE STRUCTURES
        # ========================================

        if not isinstance(
            state.get("applicants"),
            list
        ):
            state["applicants"] = []


        if not isinstance(
            state.get("loan_request"),
            dict
        ):
            state["loan_request"] = {}


        if not isinstance(
            state.get("property"),
            dict
        ):
            state["property"] = {}


        if not isinstance(
            state.get("human_review_queue"),
            list
        ):
            state["human_review_queue"] = []


        # ========================================
        # LOAD APPLICANT SAFELY
        # ========================================

        applicant = (

            state["applicants"][0]

            if len(state["applicants"]) > 0

            else {}

        )


        personal = applicant.get(
            "personal_details",
            {}
        )


        income = applicant.get(
            "income",
            {}
        )


        liabilities = applicant.get(
            "liabilities",
            {}
        )


        property_data = state.get(
            "property",
            {}
        )


        loan_request = state.get(
            "loan_request",
            {}
        )


        # ========================================
        # SAFE NUMERIC HELPER
        # ========================================

        def to_float(value, default=0.0):

            try:

                if value is None:

                    return default


                return float(value)

            except (
                TypeError,
                ValueError
            ):

                return default


        # ========================================
        # APPLICANT VALUES
        # ========================================

        dob = personal.get(
            "date_of_birth"
        )


        net_income = to_float(

            income.get(
                "net_monthly_income",

                income.get(
                    "net_income",
                    0
                )
            )

        )


        existing_emi = to_float(

            liabilities.get(
                "existing_monthly_emi",

                liabilities.get(
                    "existing_emi",
                    0
                )
            )

        )


        # ========================================
        # LOAN VALUES
        # IMPORTANT:
        # SUPPORT GRADIO + OLD PIPELINE KEYS
        # ========================================

        requested_amount = to_float(

            loan_request.get(
                "requested_amount",

                loan_request.get(
                    "requested_loan_amount",
                    0
                )
            )

        )


        tenure_years = to_float(

            loan_request.get(
                "tenure_years",

                loan_request.get(
                    "requested_tenure_years",
                    0
                )
            )

        )


        interest_rate = to_float(

            loan_request.get(
                "interest_rate",
                0
            )

        )


        # ========================================
        # PROPERTY VALUE
        # SUPPORT GRADIO property_value
        # ========================================

        property_value = (

            property_data.get(
                "property_value"
            )

            or property_data.get(
                "valuation_value"
            )

            or property_data.get(
                "market_value"
            )

            or property_data.get(
                "purchase_price"
            )

        )


        property_value = to_float(
            property_value
        )


        # ========================================
        # AGE CHECK
        # ========================================

        age = None

        age_status = "REVIEW_REQUIRED"


        if dob:

            try:

                age = calculate_age(
                    dob
                )


                age_at_maturity = (
                    age + tenure_years
                )


                if (

                    age >=
                    UNDERWRITING_POLICY[
                        "age"
                    ][
                        "minimum_age"
                    ]

                    and

                    age_at_maturity <=
                    UNDERWRITING_POLICY[
                        "age"
                    ][
                        "maximum_age_at_maturity"
                    ]

                ):

                    age_status = "PASS"


                else:

                    age_status = "FAIL"


            except Exception:

                age_status = (
                    "REVIEW_REQUIRED"
                )


        # ========================================
        # INCOME CHECK
        # ========================================

        minimum_income = (

            UNDERWRITING_POLICY[
                "income"
            ][
                "minimum_net_monthly_income"
            ]

        )


        if net_income <= 0:

            income_status = (
                "REVIEW_REQUIRED"
            )


        elif net_income >= minimum_income:

            income_status = "PASS"


        else:

            income_status = "FAIL"


        # ========================================
        # EMI CALCULATIONS
        # ========================================

        proposed_emi = None

        foir = None

        max_new_emi = None

        estimated_max_loan = None


        if (

            requested_amount > 0

            and

            interest_rate > 0

            and

            tenure_years > 0

        ):

            proposed_emi = calculate_emi(

                requested_amount,

                interest_rate,

                tenure_years

            )


        if (

            net_income > 0

            and

            proposed_emi is not None

        ):

            foir = calculate_foir(

                net_income,

                existing_emi,

                proposed_emi

            )


        if net_income > 0:

            max_new_emi = calculate_max_emi(

                net_income,

                existing_emi,

                UNDERWRITING_POLICY[
                    "foir"
                ][
                    "maximum_foir_percentage"
                ]

            )


        if (

            max_new_emi is not None

            and

            interest_rate > 0

            and

            tenure_years > 0

        ):

            estimated_max_loan = (
                calculate_max_loan_from_emi(

                    max_new_emi,

                    interest_rate,

                    tenure_years

                )
            )


        # ========================================
        # FOIR CHECK
        # ========================================

        max_foir = (

            UNDERWRITING_POLICY[
                "foir"
            ][
                "maximum_foir_percentage"
            ]

        )


        if foir is None:

            foir_status = (
                "REVIEW_REQUIRED"
            )


        elif foir <= max_foir:

            foir_status = "PASS"


        else:

            foir_status = "FAIL"


        # ========================================
        # LTV CHECK
        # ========================================

        ltv_percentage = None

        ltv_status = "REVIEW_REQUIRED"


        if (

            requested_amount > 0

            and

            property_value > 0

        ):

            ltv_percentage = round(

                (
                    requested_amount
                    / property_value
                ) * 100,

                2

            )


            max_ltv = (

                UNDERWRITING_POLICY[
                    "ltv"
                ][
                    "maximum_ltv_percentage"
                ]

            )


            if ltv_percentage <= max_ltv:

                ltv_status = "PASS"

            else:

                ltv_status = "FAIL"


        # ========================================
        # LOAN AMOUNT CHECK
        # ========================================

        min_loan = (

            UNDERWRITING_POLICY[
                "loan_amount"
            ][
                "minimum_loan_amount"
            ]

        )


        max_loan = (

            UNDERWRITING_POLICY[
                "loan_amount"
            ][
                "maximum_loan_amount"
            ]

        )


        if requested_amount <= 0:

            loan_amount_status = (
                "REVIEW_REQUIRED"
            )


        elif (

            requested_amount >= min_loan

            and

            requested_amount <= max_loan

        ):

            loan_amount_status = "PASS"


        else:

            loan_amount_status = "FAIL"


        # ========================================
        # INCOME BASED ELIGIBILITY
        # ========================================

        if estimated_max_loan is None:

            eligibility_amount_status = (
                "REVIEW_REQUIRED"
            )


        elif requested_amount <= estimated_max_loan:

            eligibility_amount_status = "PASS"


        else:

            eligibility_amount_status = "FAIL"


        # ========================================
        # COLLECT RESULTS
        # ========================================

        checks = {


            "age": {

                "status": age_status,

                "current_age": age,

                "age_at_loan_maturity":

                    (
                        age + tenure_years
                        if age is not None
                        else None
                    )

            },


            "income": {

                "status": income_status,

                "net_monthly_income":
                    net_income,

                "minimum_required_income":
                    minimum_income

            },


            "foir": {

                "status": foir_status,

                "foir_percentage":
                    foir,

                "maximum_allowed_foir":
                    max_foir,

                "existing_emi":
                    existing_emi,

                "proposed_emi":
                    proposed_emi,

                "maximum_new_emi":
                    max_new_emi

            },


            "loan_to_value": {

                "status": ltv_status,

                "property_value":
                    property_value,

                "requested_loan":
                    requested_amount,

                "ltv_percentage":
                    ltv_percentage,

                "maximum_allowed_ltv":

                    UNDERWRITING_POLICY[
                        "ltv"
                    ][
                        "maximum_ltv_percentage"
                    ]

            },


            "loan_amount": {

                "status":
                    loan_amount_status,

                "requested_amount":
                    requested_amount,

                "minimum_allowed":
                    min_loan,

                "maximum_allowed":
                    max_loan

            },


            "income_based_eligibility": {

                "status":
                    eligibility_amount_status,

                "estimated_maximum_loan":
                    estimated_max_loan,

                "requested_loan":
                    requested_amount

            }

        }


        # ========================================
        # FINAL DECISION
        # ========================================

        statuses = [

            check.get(
                "status"
            )

            for check in checks.values()

        ]


        fail_count = statuses.count(
            "FAIL"
        )


        review_count = statuses.count(
            "REVIEW_REQUIRED"
        )


        if fail_count > 0:

            decision = "NOT_ELIGIBLE"


        elif review_count > 0:

            decision = "REVIEW_REQUIRED"


        else:

            decision = "ELIGIBLE"


        # ========================================
        # BUILD RESULT
        # ========================================

        underwriting_result = {

            "checks":
                checks,

            "summary": {

                "total_checks":
                    len(checks),

                "passed":
                    statuses.count(
                        "PASS"
                    ),

                "failed":
                    fail_count,

                "review_required":
                    review_count,

                "decision":
                    decision

            }

        }


        state[
            "underwriting_result"
        ] = underwriting_result


        # ========================================
        # ADD FAILURES TO HUMAN REVIEW
        # ========================================

        for check_name, check in checks.items():

            if check.get(
                "status"
            ) in [

                "FAIL",

                "REVIEW_REQUIRED"

            ]:

                state[
                    "human_review_queue"
                ].append({

                    "type":
                        "UNDERWRITING_EXCEPTION",

                    "check":
                        check_name,

                    "status":
                        check.get(
                            "status"
                        ),

                    "details":
                        check

                })


        # ========================================
        # LOG RESULT
        # ========================================

        self.log(

            state,

            "COMPLETED",

            f"Underwriting decision: {decision}"

        )


        return state


print(
    "✅ LoanEligibilityUnderwritingAgent loaded"
)

# ===== NOTEBOOK CELL 23 =====
def generate_underwriting_recommendations(
    underwriting_result
):

    checks = underwriting_result.get(
        "checks",
        {}
    )

    recommendations = []


    # ----------------------------------------
    # FOIR RECOMMENDATION
    # ----------------------------------------

    foir_check = checks.get(
        "foir",
        {}
    )

    if foir_check.get("status") == "FAIL":

        recommendations.append({

            "type": "FOIR_EXCEEDED",

            "priority": "HIGH",

            "message":
                "Applicant's total EMI obligations "
                "exceed the maximum FOIR limit.",

            "current_foir":
                foir_check.get(
                    "foir_percentage"
                ),

            "maximum_allowed_foir":
                foir_check.get(
                    "maximum_allowed_foir"
                ),

            "recommended_action":
                "Reduce the requested loan amount, "
                "increase the loan tenure, or reduce "
                "existing liabilities."
        })


    # ----------------------------------------
    # INCOME BASED ELIGIBILITY
    # ----------------------------------------

    income_eligibility = checks.get(
        "income_based_eligibility",
        {}
    )

    if income_eligibility.get(
        "status"
    ) == "FAIL":

        requested_loan = (
            income_eligibility.get(
                "requested_loan",
                0
            )
        )

        maximum_loan = (
            income_eligibility.get(
                "estimated_maximum_loan",
                0
            )
        )

        loan_gap = (
            requested_loan
            - maximum_loan
        )

        recommendations.append({

            "type":
                "LOAN_AMOUNT_EXCEEDS_ELIGIBILITY",

            "priority": "HIGH",

            "message":
                "Requested loan amount exceeds "
                "the estimated income-based "
                "eligibility.",

            "requested_loan":
                requested_loan,

            "estimated_maximum_loan":
                maximum_loan,

            "loan_gap":
                round(
                    loan_gap,
                    2
                ),

            "recommended_action":
                f"Consider reducing the loan "
                f"amount to approximately "
                f"₹{maximum_loan:,.0f}."
        })


    # ----------------------------------------
    # LTV RECOMMENDATION
    # ----------------------------------------

    ltv_check = checks.get(
        "loan_to_value",
        {}
    )

    if ltv_check.get("status") == "FAIL":

        recommendations.append({

            "type": "LTV_EXCEEDED",

            "priority": "HIGH",

            "message":
                "Requested loan exceeds the "
                "maximum allowed Loan-to-Value ratio.",

            "current_ltv":
                ltv_check.get(
                    "ltv_percentage"
                ),

            "maximum_ltv":
                ltv_check.get(
                    "maximum_allowed_ltv"
                ),

            "recommended_action":
                "Increase the down payment or "
                "reduce the requested loan amount."
        })


    # ----------------------------------------
    # AGE RECOMMENDATION
    # ----------------------------------------

    age_check = checks.get(
        "age",
        {}
    )

    if age_check.get("status") == "FAIL":

        recommendations.append({

            "type": "AGE_ELIGIBILITY_EXCEPTION",

            "priority": "HIGH",

            "message":
                "Applicant does not meet the "
                "age eligibility requirement.",

            "recommended_action":
                "Reduce the loan tenure or "
                "consider adding an eligible "
                "co-applicant."
        })


    # ----------------------------------------
    # REVIEW REQUIRED
    # ----------------------------------------

    for check_name, check in checks.items():

        if check.get(
            "status"
        ) == "REVIEW_REQUIRED":

            recommendations.append({

                "type":
                    "MANUAL_REVIEW_REQUIRED",

                "priority":
                    "MEDIUM",

                "check":
                    check_name,

                "message":
                    f"{check_name.replace('_', ' ').title()} "
                    f"requires additional verification.",

                "recommended_action":
                    "Request missing information "
                    "or escalate the case to a "
                    "human underwriter."
            })


    return recommendations


print(
    "✅ Underwriting recommendation engine loaded"
)

# ===== NOTEBOOK CELL 24 =====
def show_underwriting_report(state):

    result = state.get(
        "underwriting_result",
        {}
    )

    recommendations = state.get(
        "underwriting_recommendations",
        []
    )

    checks = result.get(
        "checks",
        {}
    )

    summary = result.get(
        "summary",
        {}
    )

    print("=" * 70)
    print("🏦 LOAN UNDERWRITING REPORT")
    print("=" * 70)

    for check_name, check in checks.items():

        status = check.get(
            "status",
            "UNKNOWN"
        )

        if status == "PASS":
            icon = "✅"

        elif status == "FAIL":
            icon = "❌"

        else:
            icon = "⚠️"

        readable_name = (
            check_name
            .replace("_", " ")
            .title()
        )

        print(
            f"\n{icon} {readable_name}"
        )

        print(
            f"Status: {status}"
        )


    print("\n" + "=" * 70)
    print("📊 UNDERWRITING SUMMARY")
    print("=" * 70)

    print(
        f"Total Checks: "
        f"{summary.get('total_checks')}"
    )

    print(
        f"Passed: "
        f"{summary.get('passed')}"
    )

    print(
        f"Failed: "
        f"{summary.get('failed')}"
    )

    print(
        f"Review Required: "
        f"{summary.get('review_required')}"
    )

    print(
        f"\n🏦 FINAL DECISION: "
        f"{summary.get('decision')}"
    )


    print("\n" + "=" * 70)
    print("💡 RECOMMENDATIONS")
    print("=" * 70)

    if not recommendations:

        print(
            "✅ No underwriting recommendations required."
        )

    else:

        for index, recommendation in enumerate(
            recommendations,
            start=1
        ):

            print(
                f"\n{index}. "
                f"{recommendation.get('type')}"
            )

            print(
                f"   Priority: "
                f"{recommendation.get('priority')}"
            )

            print(
                f"   Issue: "
                f"{recommendation.get('message')}"
            )

            print(
                f"   Action: "
                f"{recommendation.get('recommended_action')}"
            )


show_underwriting_report(
    loan_state
)

# ===== NOTEBOOK CELL 25 =====
RISK_POLICY = {

    "risk_levels": {
        "LOW": {
            "min_score": 0,
            "max_score": 29
        },

        "MEDIUM": {
            "min_score": 30,
            "max_score": 59
        },

        "HIGH": {
            "min_score": 60,
            "max_score": 79
        },

        "CRITICAL": {
            "min_score": 80,
            "max_score": 100
        }
    },

    "risk_weights": {

        "document_missing": 15,

        "document_extraction_issue": 10,

        "document_mismatch": 30,

        "verification_review_required": 15,

        "foir_exceeded": 20,

        "income_eligibility_failed": 20,

        "ltv_exceeded": 20,

        "age_eligibility_failed": 25,

        "underwriting_review_required": 15
    }
}

print("✅ Risk policy loaded")

# ===== NOTEBOOK CELL 26 =====
def determine_risk_level(risk_score):

    if risk_score <= RISK_POLICY["risk_levels"]["LOW"]["max_score"]:

        return "LOW"

    elif risk_score <= RISK_POLICY["risk_levels"]["MEDIUM"]["max_score"]:

        return "MEDIUM"

    elif risk_score <= RISK_POLICY["risk_levels"]["HIGH"]["max_score"]:

        return "HIGH"

    else:

        return "CRITICAL"


def add_risk_factor(
    risk_factors,
    factor_type,
    score,
    reason,
    source
):

    risk_factors.append({

        "factor_type": factor_type,

        "risk_points": score,

        "reason": reason,

        "source": source
    })


print("✅ Risk scoring helpers loaded")

# ===== NOTEBOOK CELL 27 =====
# ========================================
# AGENT 6
# RISK, FRAUD & EXCEPTION DETECTION AGENT
# ========================================

class RiskFraudExceptionAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            "Risk, Fraud & Exception Detection Agent"
        )

    def run(self, state):

        self.log(
            state,
            "PROCESSING",
            "Analyzing documents, verification, "
            "underwriting risks and exceptions"
        )

        risk_score = 0
        risk_factors = []
        fraud_flags = []
        exceptions = []

        # ========================================
        # ENSURE HUMAN REVIEW QUEUE
        # ========================================

        if not isinstance(
            state.get("human_review_queue"),
            list
        ):
            state["human_review_queue"] = []

        # ========================================
        # AGENT 2 - DOCUMENT COMPLETENESS
        # ========================================

        document_inventory = state.get(
            "document_inventory",
            {}
        )

        if not isinstance(document_inventory, dict):
            document_inventory = {}

        missing_documents = document_inventory.get(
            "missing",
            []
        )

        if not isinstance(missing_documents, list):
            missing_documents = []

        missing_document_points = 0
        max_missing_document_risk = 25

        for document in missing_documents:

            base_points = (
                RISK_POLICY
                .get("risk_weights", {})
                .get("document_missing", 5)
            )

            remaining_points = (
                max_missing_document_risk
                - missing_document_points
            )

            points = min(
                base_points,
                remaining_points
            )

            if points <= 0:
                break

            risk_score += points
            missing_document_points += points

            add_risk_factor(
                risk_factors,
                "MISSING_DOCUMENT",
                points,
                f"Required document missing: {document}",
                "Document Checklist Agent"
            )

            exceptions.append({
                "type": "MISSING_DOCUMENT",
                "document": document,
                "severity": "MEDIUM"
            })

        # ========================================
        # AGENT 3 - EXTRACTION ISSUES
        # ========================================

        extracted_data = state.get(
            "extracted_data",
            {}
        )

        if not isinstance(extracted_data, dict):
            extracted_data = {}

        extracted_documents = extracted_data.get(
            "documents",
            []
        )

        if not isinstance(extracted_documents, list):
            extracted_documents = []

        extraction_issue_points = 0
        max_extraction_risk = 20

        for document in extracted_documents:

            if not isinstance(document, dict):
                continue

            extraction_status = document.get(
                "extraction_status"
            )

            extraction_issues = document.get(
                "extraction_issues",
                []
            )

            if extraction_status not in [
                "REVIEW_REQUIRED",
                "FAILED"
            ]:
                continue

            base_points = (
                RISK_POLICY
                .get("risk_weights", {})
                .get(
                    "document_extraction_issue",
                    3
                )
            )

            remaining_points = (
                max_extraction_risk
                - extraction_issue_points
            )

            points = min(
                base_points,
                remaining_points
            )

            if points <= 0:
                break

            risk_score += points
            extraction_issue_points += points

            document_type = document.get(
                "document_type",
                "UNKNOWN"
            )

            add_risk_factor(
                risk_factors,
                "DOCUMENT_EXTRACTION_ISSUE",
                points,
                f"Extraction issue detected in "
                f"{document_type}",
                "Document Intelligence Agent"
            )

            exceptions.append({
                "type": "DOCUMENT_EXTRACTION_ISSUE",
                "document_type": document_type,
                "severity": "MEDIUM",
                "issues": extraction_issues
            })

        # ========================================
        # AGENT 4 - CROSS-DOCUMENT VERIFICATION
        # ========================================

        verification_results = state.get(
            "verification_results",
            {}
        )

        if not isinstance(verification_results, dict):
            verification_results = {}

        verification_risk_points = 0
        max_verification_risk = 30

        for check_name, result in (
            verification_results.items()
        ):

            if check_name == "summary":
                continue

            if not isinstance(result, dict):
                continue

            status = result.get("status")

            if status == "MISMATCH":

                base_points = (
                    RISK_POLICY
                    .get("risk_weights", {})
                    .get(
                        "document_mismatch",
                        15
                    )
                )

                remaining_points = (
                    max_verification_risk
                    - verification_risk_points
                )

                points = min(
                    base_points,
                    remaining_points
                )

                if points <= 0:
                    break

                risk_score += points
                verification_risk_points += points

                add_risk_factor(
                    risk_factors,
                    "DOCUMENT_MISMATCH",
                    points,
                    f"Mismatch detected in "
                    f"{check_name}",
                    "Cross-Document Verification Agent"
                )

                fraud_flags.append({
                    "type": "CROSS_DOCUMENT_MISMATCH",
                    "check": check_name,
                    "severity": "HIGH"
                })

            elif status == "REVIEW_REQUIRED":

                base_points = (
                    RISK_POLICY
                    .get("risk_weights", {})
                    .get(
                        "verification_review_required",
                        5
                    )
                )

                remaining_points = (
                    max_verification_risk
                    - verification_risk_points
                )

                points = min(
                    base_points,
                    remaining_points
                )

                if points <= 0:
                    break

                risk_score += points
                verification_risk_points += points

                add_risk_factor(
                    risk_factors,
                    "VERIFICATION_REVIEW_REQUIRED",
                    points,
                    f"Manual verification required "
                    f"for {check_name}",
                    "Cross-Document Verification Agent"
                )

        # ========================================
        # AGENT 5 - UNDERWRITING RESULTS
        # ========================================

        underwriting_result = state.get(
            "underwriting_result",
            {}
        )

        if not isinstance(underwriting_result, dict):
            underwriting_result = {}

        underwriting_checks = underwriting_result.get(
            "checks",
            {}
        )

        if not isinstance(underwriting_checks, dict):
            underwriting_checks = {}

        # ========================================
        # FOIR CHECK
        # ========================================

        foir_check = underwriting_checks.get(
            "foir",
            {}
        )

        if not isinstance(foir_check, dict):
            foir_check = {}

        if foir_check.get("status") == "FAIL":

            points = (
                RISK_POLICY
                .get("risk_weights", {})
                .get("foir_exceeded", 15)
            )

            risk_score += points

            add_risk_factor(
                risk_factors,
                "FOIR_EXCEEDED",
                points,
                "Applicant FOIR exceeds the "
                "configured policy limit",
                "Underwriting Agent"
            )

            exceptions.append({
                "type": "FOIR_EXCEEDED",
                "severity": "HIGH",
                "current_foir": foir_check.get(
                    "foir_percentage"
                ),
                "maximum_allowed": foir_check.get(
                    "maximum_allowed_foir"
                )
            })

        # ========================================
        # INCOME ELIGIBILITY CHECK
        # ========================================

        income_eligibility = underwriting_checks.get(
            "income_based_eligibility",
            {}
        )

        if not isinstance(
            income_eligibility,
            dict
        ):
            income_eligibility = {}

        if (
            income_eligibility.get("status")
            == "FAIL"
        ):

            points = (
                RISK_POLICY
                .get("risk_weights", {})
                .get(
                    "income_eligibility_failed",
                    15
                )
            )

            risk_score += points

            add_risk_factor(
                risk_factors,
                "INCOME_ELIGIBILITY_FAILED",
                points,
                "Requested loan exceeds "
                "income-based eligibility",
                "Underwriting Agent"
            )

            exceptions.append({
                "type": "INCOME_ELIGIBILITY_FAILED",
                "severity": "HIGH",
                "requested_loan": (
                    income_eligibility.get(
                        "requested_loan"
                    )
                ),
                "estimated_maximum_loan": (
                    income_eligibility.get(
                        "estimated_maximum_loan"
                    )
                )
            })

        # ========================================
        # LTV CHECK
        # ========================================

        ltv_check = underwriting_checks.get(
            "loan_to_value",
            {}
        )

        if not isinstance(ltv_check, dict):
            ltv_check = {}

        if ltv_check.get("status") == "FAIL":

            points = (
                RISK_POLICY
                .get("risk_weights", {})
                .get("ltv_exceeded", 15)
            )

            risk_score += points

            add_risk_factor(
                risk_factors,
                "LTV_EXCEEDED",
                points,
                "Loan-to-Value ratio exceeds "
                "the configured policy limit",
                "Underwriting Agent"
            )

            exceptions.append({
                "type": "LTV_EXCEEDED",
                "severity": "HIGH",
                "ltv_percentage": ltv_check.get(
                    "ltv_percentage"
                ),
                "maximum_allowed": ltv_check.get(
                    "maximum_allowed_ltv"
                )
            })

        # ========================================
        # AGE CHECK
        # ========================================

        age_check = underwriting_checks.get(
            "age",
            {}
        )

        if not isinstance(age_check, dict):
            age_check = {}

        if age_check.get("status") == "FAIL":

            points = (
                RISK_POLICY
                .get("risk_weights", {})
                .get(
                    "age_eligibility_failed",
                    15
                )
            )

            risk_score += points

            add_risk_factor(
                risk_factors,
                "AGE_ELIGIBILITY_FAILED",
                points,
                "Applicant does not meet "
                "age eligibility criteria",
                "Underwriting Agent"
            )

            exceptions.append({
                "type": "AGE_ELIGIBILITY_FAILED",
                "severity": "HIGH",
                "current_age": age_check.get(
                    "current_age"
                ),
                "age_at_loan_maturity": (
                    age_check.get(
                        "age_at_loan_maturity"
                    )
                )
            })

        # ========================================
        # FINAL RISK SCORE
        # ========================================

        risk_score = min(
            int(round(risk_score)),
            100
        )

        risk_level = determine_risk_level(
            risk_score
        )

        # ========================================
        # HUMAN REVIEW DECISION
        # ========================================

        has_high_severity_exception = any(
            exception.get("severity") == "HIGH"
            for exception in exceptions
        )

        human_review_required = (
            risk_level in [
                "HIGH",
                "CRITICAL"
            ]
            or len(fraud_flags) > 0
            or has_high_severity_exception
        )

        # ========================================
        # FINAL RESULT
        # ========================================

        result = {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "fraud_flags": fraud_flags,
            "exceptions": exceptions,
            "risk_factors": risk_factors,
            "human_review_required": (
                human_review_required
            ),
            "recommendation": (
                "ESCALATE_TO_HUMAN_REVIEW"
                if human_review_required
                else "PROCEED_TO_DECISION"
            )
        }

        state["risk_assessment"] = result

        # ========================================
        # ADD HIGH-RISK ITEMS TO HUMAN REVIEW
        # ========================================

        for exception in exceptions:

            if (
                exception.get("severity")
                == "HIGH"
            ):

                state[
                    "human_review_queue"
                ].append({
                    "type": "RISK_EXCEPTION",
                    "status": "REVIEW_REQUIRED",
                    "details": exception
                })

        self.log(
            state,
            "COMPLETED",
            f"Risk Score: {risk_score}/100, "
            f"Risk Level: {risk_level}, "
            f"Exceptions: {len(exceptions)}"
        )

        return state


agent_6 = RiskFraudExceptionAgent()

print("✅ Agent 6 loaded successfully")

# ===== NOTEBOOK CELL 28 =====
class LoanCaseSummaryAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            "AI Loan Case Summary Agent"
        )


    def run(self, state):

        self.log(
            state,
            "PROCESSING",
            "Generating AI-powered loan case summary"
        )

        try:

            # ========================================
            # LOAD APPLICANT DATA
            # ========================================

            applicants = state.get(
                "applicants",
                []
            )

            applicant = (
                applicants[0]
                if applicants
                else {}
            )

            personal = applicant.get(
                "personal_details",
                {}
            )

            employment = applicant.get(
                "employment",
                {}
            )

            income = applicant.get(
                "income",
                {}
            )


            # ========================================
            # LOAD LOAN DATA
            # ========================================

            loan_request = state.get(
                "loan_request",
                {}
            )

            requested_amount = (
                loan_request.get(
                    "requested_amount"
                )
                or loan_request.get(
                    "requested_loan_amount"
                )
                or 0
            )

            tenure_years = (
                loan_request.get(
                    "tenure_years"
                )
                or loan_request.get(
                    "requested_tenure_years"
                )
                or 0
            )

            purpose = loan_request.get(
                "purpose",
                "NOT_SPECIFIED"
            )


            # ========================================
            # LOAD DOCUMENT DATA
            # ========================================

            document_inventory = state.get(
                "document_inventory",
                {}
            )

            if not isinstance(
                document_inventory,
                dict
            ):
                document_inventory = {}

            submitted_documents = (
                document_inventory.get(
                    "submitted",
                    []
                )
            )

            missing_documents = (
                document_inventory.get(
                    "missing",
                    []
                )
            )


            # ========================================
            # LOAD VERIFICATION DATA
            # ========================================

            verification_results = state.get(
                "verification_results",
                {}
            )

            if not isinstance(
                verification_results,
                dict
            ):
                verification_results = {}

            verification_summary = (
                verification_results.get(
                    "summary",
                    {}
                )
            )


            # ========================================
            # LOAD UNDERWRITING DATA
            # ========================================

            underwriting_result = state.get(
                "underwriting_result",
                {}
            )

            if not isinstance(
                underwriting_result,
                dict
            ):
                underwriting_result = {}

            underwriting_summary = (
                underwriting_result.get(
                    "summary",
                    {}
                )
            )

            underwriting_checks = (
                underwriting_result.get(
                    "checks",
                    {}
                )
            )


            # ========================================
            # LOAD RISK DATA
            # ========================================

            risk_assessment = state.get(
                "risk_assessment",
                {}
            )

            if not isinstance(
                risk_assessment,
                dict
            ):
                risk_assessment = {}

            risk_score = risk_assessment.get(
                "risk_score",
                0
            )

            risk_level = risk_assessment.get(
                "risk_level",
                "UNKNOWN"
            )

            fraud_flags = risk_assessment.get(
                "fraud_flags",
                []
            )

            exceptions = risk_assessment.get(
                "exceptions",
                []
            )

            human_review_required = (
                risk_assessment.get(
                    "human_review_required",
                    False
                )
            )


            # ========================================
            # GET FAILED UNDERWRITING CHECKS
            # ========================================

            failed_underwriting_checks = []

            if isinstance(
                underwriting_checks,
                dict
            ):

                for check_name, check in (
                    underwriting_checks.items()
                ):

                    if isinstance(check, dict):

                        if check.get(
                            "status"
                        ) == "FAIL":

                            failed_underwriting_checks.append(
                                check_name.upper()
                            )


            # ========================================
            # CREATE STRUCTURED CASE DATA
            # ========================================

            case_data = {

                "application_id": state.get(
                    "application_id"
                ),

                "applicant": {
                    "name": personal.get(
                        "full_name"
                    ),

                    "employment_type": employment.get(
                        "employment_type"
                    ),

                    "employer": employment.get(
                        "employer_or_business"
                    ),

                    "years_of_experience": employment.get(
                        "years_of_experience"
                    ),

                    "current_employment_years": employment.get(
                        "current_employment_years"
                    ),

                    "net_monthly_income": income.get(
                        "net_monthly_income"
                    )
                },

                "loan_request": {
                    "requested_amount": requested_amount,
                    "tenure_years": tenure_years,
                    "purpose": purpose
                },

                "documents": {
                    "submitted_count": len(
                        submitted_documents
                    ),

                    "missing_documents": missing_documents
                },

                "verification": verification_summary,

                "underwriting": {
                    "decision": underwriting_summary.get(
                        "decision"
                    ),

                    "failed_checks":
                        failed_underwriting_checks,

                    "checks":
                        underwriting_checks
                },

                "risk": {
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "fraud_flags": fraud_flags,
                    "exceptions": exceptions,
                    "human_review_required":
                        human_review_required
                }
            }


            # ========================================
            # AI SUMMARY PROMPT
            # ========================================

            prompt = f"""
You are an AI Loan Case Summary Agent for an Indian
Home Loan Processing System.

Analyze the following loan application data and create
a concise structured summary.

CASE DATA:

{json.dumps(
    case_data,
    indent=2,
    default=str
)}

Return ONLY valid JSON.

Use EXACTLY this structure:

{{
    "executive_summary": "brief summary",

    "applicant_profile": {{
        "name": "applicant name",
        "employment": "employment summary",
        "net_monthly_income": "income"
    }},

    "loan_request_summary": {{
        "requested_amount": "amount",
        "tenure_years": "years",
        "purpose": "purpose"
    }},

    "verification_summary":
        "verification result summary",

    "key_findings": [
        "finding 1"
    ],

    "risk_observations": [
        "risk observation 1"
    ],

    "recommended_actions": [
        "recommended action 1"
    ],

    "human_review_required": true,

    "decision_recommendation":
        "PROCEED_TO_DECISION_OR_ESCALATE_TO_HUMAN_REVIEW",

    "decision_reason":
        "clear reason"
}}

IMPORTANT RULES:

1. Do not invent information.
2. Use only the supplied case data.
3. Clearly mention failed underwriting checks.
4. Clearly mention verification issues if present.
5. Clearly mention risk exceptions.
6. If underwriting decision is NOT_ELIGIBLE,
   do not recommend direct approval.
7. If human review is required,
   decision_recommendation must be
   ESCALATE_TO_HUMAN_REVIEW.
8. Keep recommendations actionable.
9. Return ONLY valid JSON.
"""


            # ========================================
            # CALL LLM
            # ========================================

            response = call_llm(
                prompt
            )

            ai_summary = extract_json(
                response
            )


            # ========================================
            # HANDLE LLM FAILURE
            # ========================================

            if (
                not isinstance(
                    ai_summary,
                    dict
                )
                or ai_summary.get(
                    "error"
                ) == "Failed to parse JSON"
            ):

                ai_summary = {

                    "executive_summary":
                        "AI summary could not be generated.",

                    "applicant_profile": {
                        "name": personal.get(
                            "full_name"
                        ),

                        "employment":
                            employment.get(
                                "employment_type"
                            ),

                        "net_monthly_income":
                            income.get(
                                "net_monthly_income"
                            )
                    },

                    "loan_request_summary": {
                        "requested_amount":
                            requested_amount,

                        "tenure_years":
                            tenure_years,

                        "purpose":
                            purpose
                    },

                    "verification_summary":
                        verification_summary,

                    "key_findings":
                        failed_underwriting_checks,

                    "risk_observations": [
                        f"Risk score: {risk_score}",
                        f"Risk level: {risk_level}"
                    ],

                    "recommended_actions": [],

                    "human_review_required":
                        human_review_required,

                    "decision_recommendation":

                        "ESCALATE_TO_HUMAN_REVIEW"

                        if human_review_required

                        else

                        "PROCEED_TO_DECISION",

                    "decision_reason":
                        "Fallback summary generated from "
                        "deterministic agent results.",

                    "llm_status":
                        "FALLBACK"
                }

            else:

                ai_summary[
                    "llm_status"
                ] = "SUCCESS"


            # ========================================
            # STORE AI SUMMARY
            # ========================================

            state[
                "ai_case_summary"
            ] = ai_summary


            self.log(
                state,
                "COMPLETED",
                f"AI case summary generated. "
                f"LLM Status: "
                f"{ai_summary.get('llm_status')}"
            )


        except Exception as e:

            # ========================================
            # SAFE FALLBACK
            # ========================================

            state[
                "ai_case_summary"
            ] = {

                "executive_summary":
                    "AI case summary generation failed.",

                "human_review_required":
                    True,

                "decision_recommendation":
                    "ESCALATE_TO_HUMAN_REVIEW",

                "decision_reason":
                    str(e),

                "llm_status":
                    "FAILED"
            }


            self.log(
                state,
                "WARNING",
                f"AI summary failed: {str(e)}"
            )


        return state

# ===== NOTEBOOK CELL 29 =====
# ========================================
# AGENT 8
# FINAL LOAN DECISION & ROUTING AGENT
# ========================================

class FinalLoanDecisionAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            "Final Loan Decision & Routing Agent"
        )


    def run(self, state):

        self.log(
            state,
            "PROCESSING",
            "Combining verification, underwriting, "
            "risk, and AI summary results"
        )


        # ========================================
        # LOAD AGENT 4 - VERIFICATION
        # ========================================

        verification_results = state.get(
            "verification_results",
            {}
        )

        if not isinstance(
            verification_results,
            dict
        ):
            verification_results = {}


        verification_summary = (
            verification_results.get(
                "summary",
                {}
            )
        )

        if not isinstance(
            verification_summary,
            dict
        ):
            verification_summary = {}


        # ========================================
        # LOAD AGENT 5 - UNDERWRITING
        # ========================================

        underwriting_result = state.get(
            "underwriting_result",
            {}
        )

        if not isinstance(
            underwriting_result,
            dict
        ):
            underwriting_result = {}


        underwriting_summary = (
            underwriting_result.get(
                "summary",
                {}
            )
        )

        if not isinstance(
            underwriting_summary,
            dict
        ):
            underwriting_summary = {}


        underwriting_checks = (
            underwriting_result.get(
                "checks",
                {}
            )
        )

        if not isinstance(
            underwriting_checks,
            dict
        ):
            underwriting_checks = {}


        # ========================================
        # LOAD AGENT 6 - RISK
        # ========================================

        risk_assessment = state.get(
            "risk_assessment",
            {}
        )

        if not isinstance(
            risk_assessment,
            dict
        ):
            risk_assessment = {}


        # ========================================
        # LOAD AGENT 7 - AI SUMMARY
        # ========================================

        ai_summary = state.get(
            "ai_case_summary",
            {}
        )

        if not isinstance(
            ai_summary,
            dict
        ):
            ai_summary = {}


        # ========================================
        # AI SUMMARY STATUS
        # ========================================

        ai_llm_status = ai_summary.get(
            "llm_status",
            ""
        )


        ai_summary_available = (
            bool(ai_summary)
            and
            ai_llm_status == "SUCCESS"
        )


        # ========================================
        # AUTHORITATIVE VALUES
        # ========================================

        verification_status = (
            verification_summary.get(
                "overall_status",
                "UNKNOWN"
            )
        )


        underwriting_decision = (
            underwriting_summary.get(
                "decision",
                "UNKNOWN"
            )
        )


        risk_score = risk_assessment.get(
            "risk_score",
            0
        )


        risk_level = risk_assessment.get(
            "risk_level",
            "UNKNOWN"
        )


        human_review_required = risk_assessment.get(
            "human_review_required",
            False
        )


        fraud_flags = risk_assessment.get(
            "fraud_flags",
            []
        )

        if not isinstance(
            fraud_flags,
            list
        ):
            fraud_flags = []


        exceptions = risk_assessment.get(
            "exceptions",
            []
        )

        if not isinstance(
            exceptions,
            list
        ):
            exceptions = []


        # ========================================
        # GET FAILED UNDERWRITING CHECKS
        # ========================================

        failed_checks = []


        for check_name, check_result in (
            underwriting_checks.items()
        ):

            if not isinstance(
                check_result,
                dict
            ):
                continue


            if check_result.get(
                "status"
            ) == "FAIL":

                failed_checks.append(
                    check_name.upper()
                )


        failed_check_count = len(
            failed_checks
        )


        # ========================================
        # FINAL DECISION
        # ========================================

        decision = None

        routing = None

        decision_reasons = []


        # ========================================
        # RULE 1
        # FRAUD FLAGS
        # ========================================

        if len(fraud_flags) > 0:

            decision = (
                "ESCALATE_TO_HUMAN_REVIEW"
            )

            routing = (
                "FRAUD_RISK_TEAM"
            )

            decision_reasons.append(
                "Fraud indicators were detected."
            )


        # ========================================
        # RULE 2
        # SEVERE UNDERWRITING FAILURE
        #
        # IMPORTANT:
        # This rule comes BEFORE HIGH/CRITICAL
        # risk escalation.
        #
        # This allows genuinely severe cases
        # to be rejected instead of automatically
        # going to human review.
        # ========================================

        elif (

            underwriting_decision
            == "NOT_ELIGIBLE"

            and

            risk_level
            == "CRITICAL"

            and

            failed_check_count >= 3

            and

            risk_score >= 90
        ):

            decision = (
                "REJECTED"
            )

            routing = (
                "APPLICATION_REJECTION"
            )

            decision_reasons.append(
                "Application failed multiple "
                "critical underwriting requirements."
            )

            decision_reasons.append(
                f"Critical risk score: "
                f"{risk_score}/100."
            )

            decision_reasons.append(
                f"{failed_check_count} underwriting "
                f"checks failed."
            )


        # ========================================
        # RULE 3
        # HIGH / CRITICAL RISK
        #
        # Less severe cases go to human review.
        # ========================================

        elif risk_level in [
            "HIGH",
            "CRITICAL"
        ]:

            decision = (
                "ESCALATE_TO_HUMAN_REVIEW"
            )

            routing = (
                "SENIOR_UNDERWRITER"
            )

            decision_reasons.append(
                f"Risk level is {risk_level}."
            )


        # ========================================
        # RULE 4
        # HUMAN REVIEW REQUIRED
        # ========================================

        elif human_review_required:

            decision = (
                "ESCALATE_TO_HUMAN_REVIEW"
            )

            routing = (
                "LOAN_REVIEW_TEAM"
            )

            decision_reasons.append(
                "Risk assessment requires "
                "human review."
            )


        # ========================================
        # RULE 5
        # UNDERWRITING NOT ELIGIBLE
        # ========================================

        elif underwriting_decision == (
            "NOT_ELIGIBLE"
        ):

            decision = (
                "REJECTED"
            )

            routing = (
                "APPLICATION_REJECTION"
            )

            decision_reasons.append(
                "Applicant does not meet "
                "underwriting eligibility "
                "requirements."
            )


        # ========================================
        # RULE 6
        # VERIFICATION ISSUE
        # ========================================

        elif verification_status in [

            "REVIEW_REQUIRED",

            "PARTIALLY_VERIFIED",

            "NOT_VERIFIED"

        ]:

            decision = (
                "ESCALATE_TO_HUMAN_REVIEW"
            )

            routing = (
                "DOCUMENT_VERIFICATION_TEAM"
            )

            decision_reasons.append(
                f"Verification status is "
                f"{verification_status}."
            )


        # ========================================
        # RULE 7
        # FULL APPROVAL
        # ========================================

        elif (

            underwriting_decision
            == "ELIGIBLE"

            and

            verification_status
            == "VERIFIED"

            and

            risk_level in [
                "LOW",
                "MEDIUM"
            ]

            and

            not human_review_required
        ):

            decision = (
                "APPROVED"
            )

            routing = (
                "LOAN_APPROVAL_PROCESSING"
            )

            decision_reasons.append(
                "Verification, underwriting, "
                "and risk checks passed."
            )


        # ========================================
        # FALLBACK
        # ========================================

        else:

            decision = (
                "ESCALATE_TO_HUMAN_REVIEW"
            )

            routing = (
                "LOAN_REVIEW_TEAM"
            )

            decision_reasons.append(
                "Unable to determine an "
                "automatic loan decision."
            )


        # ========================================
        # ADD FAILED CHECK DETAILS
        # ========================================

        if failed_checks:

            decision_reasons.append(
                "Failed underwriting checks: "
                + ", ".join(
                    failed_checks
                )
            )


        # ========================================
        # ADD EXCEPTION DETAILS
        # ========================================

        if exceptions:

            decision_reasons.append(
                f"{len(exceptions)} "
                f"risk/processing exception(s) detected."
            )


        # ========================================
        # AI SUMMARY STATUS
        # ========================================

        ai_summary_status = (

            "AVAILABLE"

            if ai_summary_available

            else "NOT_AVAILABLE"
        )


        # ========================================
        # BUILD FINAL RESULT
        # ========================================

        final_result = {

            "application_id":
                state.get(
                    "application_id"
                ),

            "final_decision":
                decision,

            "routing":
                routing,

            "decision_reasons":
                decision_reasons,

            "verification_status":
                verification_status,

            "underwriting_decision":
                underwriting_decision,

            "failed_underwriting_checks":
                failed_checks,

            "risk_score":
                risk_score,

            "risk_level":
                risk_level,

            "human_review_required":
                human_review_required,

            "fraud_flags":
                fraud_flags,

            "exceptions":
                exceptions,

            "ai_summary_available":
                ai_summary_available,

            "ai_summary_status":
                ai_summary_status,

            "ai_llm_status":
                ai_llm_status
        }


        # ========================================
        # SAVE FINAL DECISION
        # ========================================

        state[
            "final_decision"
        ] = final_result


        # ========================================
        # LOG RESULT
        # ========================================

        self.log(
            state,
            "COMPLETED",
            f"Final Decision: {decision}"
        )


        return state


print(
    "✅ Updated FinalLoanDecisionAgent loaded"
)

# ===== NOTEBOOK CELL 30 =====
# ========================================
# CELL 66 - AGENT 9
# HUMAN REVIEW & CASE MANAGEMENT AGENT
# UPDATED VERSION
# ========================================


class HumanReviewCaseManagementAgent(BaseAgent):


    def __init__(self):

        super().__init__(
            "Human Review & Case Management Agent"
        )


    def run(self, state):


        self.log(
            state,
            "PROCESSING",
            "Creating and managing human review case"
        )


        # ========================================
        # GET FINAL DECISION
        # ========================================

        final_decision = state.get(
            "final_decision",
            {}
        )


        # ========================================
        # GET AGENT RESULTS
        # ========================================

        verification_results = state.get(
            "verification_results",
            {}
        )


        verification_summary = (
            verification_results.get(
                "summary",
                {}
            )
        )


        underwriting_result = state.get(
            "underwriting_result",
            {}
        )


        underwriting_checks = (
            underwriting_result.get(
                "checks",
                {}
            )
        )


        risk_assessment = state.get(
            "risk_assessment",
            {}
        )


        # ========================================
        # GET AI SUMMARY
        # AGENT 7 USES ai_case_summary
        # ========================================

        ai_summary = state.get(
            "ai_case_summary",
            {}
        )


        # ========================================
        # AUTHORITATIVE VALUES
        # ========================================

        application_id = (
            final_decision.get(
                "application_id"
            )
            or
            state.get(
                "application_id"
            )
            or
            "UNKNOWN"
        )


        system_decision = (
            final_decision.get(
                "final_decision",
                "UNKNOWN"
            )
        )


        routing = (
            final_decision.get(
                "routing",
                "LOAN_REVIEW_TEAM"
            )
        )


        verification_status = (
            final_decision.get(
                "verification_status"
            )
            or
            verification_summary.get(
                "overall_status",
                "UNKNOWN"
            )
        )


        underwriting_decision = (
            final_decision.get(
                "underwriting_decision",
                "UNKNOWN"
            )
        )


        risk_score = (
            final_decision.get(
                "risk_score",
                0
            )
        )


        risk_level = (
            final_decision.get(
                "risk_level",
                "UNKNOWN"
            )
        )


        human_review_required = (
            final_decision.get(
                "human_review_required",
                False
            )
        )


        fraud_flags = (
            final_decision.get(
                "fraud_flags",
                []
            )
        )


        exceptions = (
            final_decision.get(
                "exceptions",
                []
            )
        )


        failed_underwriting_checks = (
            final_decision.get(
                "failed_underwriting_checks",
                []
            )
        )


        # ========================================
        # DETERMINE IF CASE IS REQUIRED
        # ========================================

        review_required = (

            system_decision
            == "ESCALATE_TO_HUMAN_REVIEW"

            or

            human_review_required

        )


        # ========================================
        # NO HUMAN REVIEW REQUIRED
        # ========================================

        if not review_required:


            review_case = {

                "case_created": False,

                "application_id":
                    application_id,

                "review_required":
                    False,

                "case_status":
                    "NOT_REQUIRED",

                "review_items":
                    [],

                "total_review_items":
                    0

            }


            state[
                "human_review_case"
            ] = review_case


            self.log(
                state,
                "COMPLETED",
                "Human review not required"
            )


            return state


        # ========================================
        # CREATE CASE ID
        # ========================================

        case_id = (
            f"REVIEW-{application_id}"
        )


        # ========================================
        # BUILD REVIEW ITEMS
        # ========================================

        review_items = []


        # ----------------------------------------
        # UNDERWRITING FAILURES
        # ----------------------------------------

        for check_name in failed_underwriting_checks:


            check_data = (
                underwriting_checks.get(
                    check_name.lower(),
                    {}
                )
            )


            review_items.append({

                "category":
                    "UNDERWRITING",

                "issue":
                    check_name,

                "details":
                    check_data,

                "action_required":

                    "Review underwriting failure and "
                    "determine whether the application "
                    "can be restructured or requires rejection.",

                "status":
                    "PENDING_REVIEW"

            })


        # ========================================
        # ADD EXCEPTIONS
        # REMOVE DUPLICATES
        # ========================================

        existing_exception_keys = set()


        for exception in exceptions:


            exception_type = (
                exception.get(
                    "type",
                    "UNKNOWN_EXCEPTION"
                )
            )


            document_type = (
                exception.get(
                    "document_type",
                    ""
                )
            )


            exception_key = (
                f"{exception_type}_"
                f"{document_type}"
            )


            if (
                exception_key
                in existing_exception_keys
            ):

                continue


            existing_exception_keys.add(
                exception_key
            )


            review_items.append({

                "category":
                    "EXCEPTION",

                "issue":
                    exception_type,

                "severity":
                    exception.get(
                        "severity",
                        "UNKNOWN"
                    ),

                "details":
                    exception,

                "action_required":

                    "Review and resolve exception.",

                "status":
                    "PENDING_REVIEW"

            })


        # ========================================
        # VERIFICATION ISSUE
        # ========================================

        if verification_status in [

            "PARTIALLY_VERIFIED",

            "REVIEW_REQUIRED",

            "FAILED"

        ]:


            review_items.append({

                "category":
                    "VERIFICATION",

                "issue":
                    verification_status,

                "details":
                    verification_summary,

                "action_required":

                    "Review incomplete or unresolved "
                    "verification results.",

                "status":
                    "PENDING_REVIEW"

            })


        # ========================================
        # FRAUD FLAGS
        # ========================================

        for fraud_flag in fraud_flags:


            review_items.append({

                "category":
                    "FRAUD",

                "issue":
                    str(fraud_flag),

                "action_required":

                    "Investigate fraud indicator before "
                    "any loan decision is finalized.",

                "status":
                    "PENDING_REVIEW"

            })


        # ========================================
        # DETERMINE PRIORITY
        # ========================================

        priority = "NORMAL"


        # HIGH PRIORITY CONDITIONS

        high_severity_exception = any(

            exception.get(
                "severity"
            )

            in [

                "HIGH",

                "CRITICAL"

            ]

            for exception in exceptions

        )


        if len(fraud_flags) > 0:

            priority = "CRITICAL"


        elif high_severity_exception:

            priority = "HIGH"


        elif underwriting_decision == "NOT_ELIGIBLE":

            priority = "HIGH"


        elif risk_level == "MEDIUM":

            priority = "MEDIUM"


        # ========================================
        # AI SUMMARY DATA
        # ========================================

        ai_executive_summary = (

            ai_summary.get(
                "executive_summary"
            )

            if ai_summary

            else None

        )


        ai_recommended_actions = (

            ai_summary.get(
                "recommended_actions",
                []
            )

            if ai_summary

            else []

        )


        ai_llm_status = (

            ai_summary.get(
                "llm_status",
                "NOT_AVAILABLE"
            )

            if ai_summary

            else "NOT_AVAILABLE"

        )


        # ========================================
        # BUILD HUMAN REVIEW CASE
        # ========================================

        review_case = {


            "case_created":
                True,


            "case_id":
                case_id,


            "application_id":
                application_id,


            "review_required":
                True,


            "case_status":
                "OPEN",


            "priority":
                priority,


            "assigned_team":
                routing,


            "final_system_decision":
                system_decision,


            "underwriting_decision":
                underwriting_decision,


            "verification_status":
                verification_status,


            "risk_score":
                risk_score,


            "risk_level":
                risk_level,


            "review_items":
                review_items,


            "total_review_items":
                len(review_items),


            "fraud_flags":
                fraud_flags,


            "exceptions":
                exceptions,


            "failed_underwriting_checks":
                failed_underwriting_checks,


            # ------------------------------------
            # AGENT 7 AI SUMMARY
            # ------------------------------------

            "ai_summary_available":
                bool(ai_summary),


            "ai_llm_status":
                ai_llm_status,


            "ai_executive_summary":
                ai_executive_summary,


            "ai_recommended_actions":
                ai_recommended_actions,


            # ------------------------------------
            # ACTIONS AVAILABLE TO REVIEWER
            # ------------------------------------

            "reviewer_actions": [

                "REVIEW_APPLICATION",

                "REQUEST_ADDITIONAL_DOCUMENTS",

                "REQUEST_DATA_CORRECTION",

                "APPROVE_EXCEPTION",

                "RESTRUCTURE_LOAN",

                "REJECT_APPLICATION",

                "APPROVE_APPLICATION"

            ]

        }


        # ========================================
        # SAVE HUMAN REVIEW CASE
        # ========================================

        state[
            "human_review_case"
        ] = review_case


        # ========================================
        # UPDATE HUMAN REVIEW QUEUE
        # PREVENT DUPLICATE CASES
        # ========================================

        existing_queue = state.get(
            "human_review_queue",
            []
        )


        cleaned_queue = []


        for item in existing_queue:


            # Skip old copy of same review case
            if (

                isinstance(
                    item,
                    dict
                )

                and

                item.get(
                    "case_id"
                )
                == case_id

            ):

                continue


            cleaned_queue.append(
                item
            )


        # Add only latest version
        cleaned_queue.append(
            review_case
        )


        state[
            "human_review_queue"
        ] = cleaned_queue


        # ========================================
        # LOG RESULT
        # ========================================

        self.log(
            state,
            "COMPLETED",
            f"Human review case created: "
            f"{case_id} | "
            f"Priority: {priority} | "
            f"Review Items: {len(review_items)}"
        )


        return state


print(
    "✅ Updated HumanReviewCaseManagementAgent loaded"
)

# ===== NOTEBOOK CELL 31 =====
# ========================================
# CELL 68 - AGENT 10
# HUMAN REVIEWER DECISION & RESOLUTION AGENT
# ========================================


class HumanReviewerDecisionAgent(BaseAgent):


    def __init__(self):

        super().__init__(
            "Human Reviewer Decision & Resolution Agent"
        )


    def run(
        self,
        state,
        reviewer_action=None,
        reviewer_notes=None,
        reviewer_id="HUMAN_REVIEWER"
    ):


        self.log(
            state,
            "PROCESSING",
            "Processing human reviewer decision"
        )


        # ========================================
        # GET HUMAN REVIEW CASE
        # ========================================

        review_case = state.get(
            "human_review_case",
            {}
        )


        # ========================================
        # VALIDATE REVIEW CASE
        # ========================================

        if not review_case:


            result = {

                "decision_processed": False,

                "status": "NO_REVIEW_CASE",

                "message":
                    "No human review case found."

            }


            state[
                "human_review_decision"
            ] = result


            self.log(
                state,
                "FAILED",
                "No human review case found"
            )


            return state


        # ========================================
        # CHECK IF CASE REQUIRES REVIEW
        # ========================================

        if not review_case.get(
            "review_required",
            False
        ):


            result = {

                "decision_processed": False,

                "status": "REVIEW_NOT_REQUIRED",

                "case_id":
                    review_case.get(
                        "case_id"
                    ),

                "message":
                    "Human review is not required."

            }


            state[
                "human_review_decision"
            ] = result


            self.log(
                state,
                "COMPLETED",
                "Human review not required"
            )


            return state


        # ========================================
        # VALID REVIEWER ACTIONS
        # ========================================

        valid_actions = [

            "REVIEW_APPLICATION",

            "REQUEST_ADDITIONAL_DOCUMENTS",

            "REQUEST_DATA_CORRECTION",

            "APPROVE_EXCEPTION",

            "RESTRUCTURE_LOAN",

            "REJECT_APPLICATION",

            "APPROVE_APPLICATION"

        ]


        # ========================================
        # NO ACTION PROVIDED
        # ========================================

        if reviewer_action is None:


            result = {

                "decision_processed": False,

                "status": "AWAITING_REVIEWER_ACTION",

                "case_id":
                    review_case.get(
                        "case_id"
                    ),

                "available_actions":
                    valid_actions,

                "message":
                    "Human reviewer action is required."

            }


            state[
                "human_review_decision"
            ] = result


            self.log(
                state,
                "COMPLETED",
                "Awaiting human reviewer action"
            )


            return state


        # ========================================
        # NORMALIZE ACTION
        # ========================================

        reviewer_action = (
            str(reviewer_action)
            .strip()
            .upper()
        )


        # ========================================
        # VALIDATE ACTION
        # ========================================

        if reviewer_action not in valid_actions:


            result = {

                "decision_processed": False,

                "status": "INVALID_REVIEWER_ACTION",

                "case_id":
                    review_case.get(
                        "case_id"
                    ),

                "received_action":
                    reviewer_action,

                "available_actions":
                    valid_actions

            }


            state[
                "human_review_decision"
            ] = result


            self.log(
                state,
                "FAILED",
                f"Invalid reviewer action: "
                f"{reviewer_action}"
            )


            return state


        # ========================================
        # DEFAULT VALUES
        # ========================================

        final_decision = None

        case_status = None

        application_status = None

        routing = None

        resolution_message = None

        next_actions = []


        # ========================================
        # ACTION 1
        # REVIEW APPLICATION
        # ========================================

        if reviewer_action == "REVIEW_APPLICATION":


            final_decision = (
                "PENDING_HUMAN_REVIEW"
            )


            case_status = (
                "IN_REVIEW"
            )


            application_status = (
                "UNDER_HUMAN_REVIEW"
            )


            routing = (
                review_case.get(
                    "assigned_team",
                    "LOAN_REVIEW_TEAM"
                )
            )


            resolution_message = (
                "Application is under active "
                "human review."
            )


            next_actions = [

                "ANALYZE_REVIEW_ITEMS",

                "SELECT_FINAL_REVIEWER_ACTION"

            ]


        # ========================================
        # ACTION 2
        # REQUEST ADDITIONAL DOCUMENTS
        # ========================================

        elif (
            reviewer_action
            == "REQUEST_ADDITIONAL_DOCUMENTS"
        ):


            final_decision = (
                "PENDING_ADDITIONAL_DOCUMENTS"
            )


            case_status = (
                "WAITING_FOR_DOCUMENTS"
            )


            application_status = (
                "DOCUMENTS_REQUIRED"
            )


            routing = (
                "DOCUMENT_COLLECTION_TEAM"
            )


            resolution_message = (
                "Additional documents have been "
                "requested from the applicant."
            )


            next_actions = [

                "COLLECT_REQUESTED_DOCUMENTS",

                "RERUN_DOCUMENT_EXTRACTION",

                "RERUN_VERIFICATION",

                "RERUN_UNDERWRITING"

            ]


        # ========================================
        # ACTION 3
        # REQUEST DATA CORRECTION
        # ========================================

        elif (
            reviewer_action
            == "REQUEST_DATA_CORRECTION"
        ):


            final_decision = (
                "PENDING_DATA_CORRECTION"
            )


            case_status = (
                "WAITING_FOR_CORRECTION"
            )


            application_status = (
                "DATA_CORRECTION_REQUIRED"
            )


            routing = (
                "APPLICATION_PROCESSING_TEAM"
            )


            resolution_message = (
                "Application data correction "
                "has been requested."
            )


            next_actions = [

                "CORRECT_APPLICATION_DATA",

                "RERUN_VERIFICATION",

                "RERUN_UNDERWRITING",

                "RERUN_RISK_ASSESSMENT"

            ]


        # ========================================
        # ACTION 4
        # APPROVE EXCEPTION
        # ========================================

        elif (
            reviewer_action
            == "APPROVE_EXCEPTION"
        ):


            final_decision = (
                "EXCEPTION_APPROVED"
            )


            case_status = (
                "EXCEPTION_APPROVED"
            )


            application_status = (
                "APPROVED_WITH_EXCEPTION"
            )


            routing = (
                "LOAN_APPROVAL_PROCESSING"
            )


            resolution_message = (
                "Reviewer approved the application "
                "exception. Application can proceed "
                "for approval processing."
            )


            next_actions = [

                "RECORD_EXCEPTION_APPROVAL",

                "CONTINUE_LOAN_PROCESSING"

            ]


        # ========================================
        # ACTION 5
        # RESTRUCTURE LOAN
        # ========================================

        elif (
            reviewer_action
            == "RESTRUCTURE_LOAN"
        ):


            final_decision = (
                "LOAN_RESTRUCTURING_REQUIRED"
            )


            case_status = (
                "RESTRUCTURING_IN_PROGRESS"
            )


            application_status = (
                "PENDING_RESTRUCTURED_LOAN"
            )


            routing = (
                "LOAN_RESTRUCTURING_TEAM"
            )


            resolution_message = (
                "Loan restructuring has been "
                "initiated to address underwriting "
                "exceptions."
            )


            next_actions = [

                "UPDATE_LOAN_AMOUNT_OR_TENURE",

                "RECALCULATE_EMI",

                "RERUN_UNDERWRITING",

                "RERUN_RISK_ASSESSMENT"

            ]


        # ========================================
        # ACTION 6
        # REJECT APPLICATION
        # ========================================

        elif (
            reviewer_action
            == "REJECT_APPLICATION"
        ):


            final_decision = (
                "REJECTED"
            )


            case_status = (
                "CLOSED"
            )


            application_status = (
                "REJECTED"
            )


            routing = (
                "APPLICATION_CLOSURE"
            )


            resolution_message = (
                "Application has been rejected "
                "following human review."
            )


            next_actions = [

                "GENERATE_REJECTION_COMMUNICATION",

                "CLOSE_APPLICATION"

            ]


        # ========================================
        # ACTION 7
        # APPROVE APPLICATION
        # ========================================

        elif (
            reviewer_action
            == "APPROVE_APPLICATION"
        ):


            final_decision = (
                "APPROVED"
            )


            case_status = (
                "CLOSED"
            )


            application_status = (
                "APPROVED"
            )


            routing = (
                "LOAN_APPROVAL_PROCESSING"
            )


            resolution_message = (
                "Application has been approved "
                "following human review."
            )


            next_actions = [

                "GENERATE_SANCTION_DETAILS",

                "START_LOAN_APPROVAL_PROCESSING"

            ]


        # ========================================
        # BUILD REVIEW DECISION
        # ========================================

        human_decision = {


            "decision_processed":
                True,


            "case_id":

                review_case.get(
                    "case_id"
                ),


            "application_id":

                review_case.get(
                    "application_id"
                ),


            "reviewer_id":
                reviewer_id,


            "reviewer_action":
                reviewer_action,


            "reviewer_notes":
                reviewer_notes,


            "previous_system_decision":

                review_case.get(
                    "final_system_decision"
                ),


            "final_decision":
                final_decision,


            "case_status":
                case_status,


            "application_status":
                application_status,


            "routing":
                routing,


            "resolution_message":
                resolution_message,


            "next_actions":
                next_actions

        }


        # ========================================
        # SAVE HUMAN DECISION
        # ========================================

        state[
            "human_review_decision"
        ] = human_decision


        # ========================================
        # UPDATE REVIEW CASE
        # ========================================

        review_case[
            "case_status"
        ] = case_status


        review_case[
            "reviewer_decision"
        ] = reviewer_action


        review_case[
            "final_human_decision"
        ] = final_decision


        review_case[
            "reviewer_notes"
        ] = reviewer_notes


        review_case[
            "reviewer_id"
        ] = reviewer_id


        # ========================================
        # UPDATE FINAL DECISION
        # ========================================

        if state.get(
            "final_decision"
        ):


            state[
                "final_decision"
            ][
                "human_reviewer_override"
            ] = True


            state[
                "final_decision"
            ][
                "human_reviewer_decision"
            ] = final_decision


            state[
                "final_decision"
            ][
                "final_decision"
            ] = final_decision


            state[
                "final_decision"
            ][
                "routing"
            ] = routing


        # ========================================
        # UPDATE HUMAN REVIEW QUEUE
        # ========================================

        human_review_queue = state.get(
            "human_review_queue",
            []
        )


        updated_queue = []


        for item in human_review_queue:


            if (

                isinstance(
                    item,
                    dict
                )

                and

                item.get(
                    "case_id"
                )
                == review_case.get(
                    "case_id"
                )

            ):


                updated_queue.append(
                    review_case
                )


            else:

                updated_queue.append(
                    item
                )


        state[
            "human_review_queue"
        ] = updated_queue


        # ========================================
        # LOG RESULT
        # ========================================

        self.log(
            state,
            "COMPLETED",
            f"Human reviewer decision: "
            f"{final_decision}"
        )


        return state


print(
    "✅ HumanReviewerDecisionAgent loaded"
)

# ===== NOTEBOOK CELL 32 =====
# ========================================
# CELL XX - AGENT 11
# LOAN RESTRUCTURING, REASSESSMENT
# & FINAL RESOLUTION AGENT
# UPDATED VERSION
# ========================================


class LoanRestructuringReassessmentAgent(BaseAgent):


    def __init__(self):

        super().__init__(
            "Loan Restructuring, Reassessment & Final Resolution Agent"
        )


    def run(self, state):


        self.log(
            state,
            "PROCESSING",
            "Processing loan restructuring, reassessment, "
            "and final resolution"
        )


        # ========================================
        # GET AGENT RESULTS
        # ========================================

        # Agent 10 reviewer decision
        reviewer_decision = (

            state.get(
                "human_reviewer_decision"
            )

            or

            state.get(
                "reviewer_decision"
            )

            or

            state.get(
                "human_review_decision"
            )

            or

            {}
        )


        underwriting_result = state.get(
            "underwriting_result",
            {}
        )


        risk_assessment = state.get(
            "risk_assessment",
            {}
        )


        verification_results = state.get(
            "verification_results",
            {}
        )


        final_system_decision = state.get(
            "final_decision",
            {}
        )


        # ========================================
        # GET APPLICANT
        # ========================================

        applicants = state.get(
            "applicants",
            []
        )


        applicant = {}

        if applicants:

            applicant = applicants[0]


        income = applicant.get(
            "income",
            {}
        )


        liabilities = applicant.get(
            "liabilities",
            {}
        )


        # ========================================
        # GET REVIEWER ACTION
        # ========================================

        reviewer_action = reviewer_decision.get(
            "reviewer_action"
        )


        if not reviewer_action:

            reviewer_action = reviewer_decision.get(
                "action"
            )


        if not reviewer_action:

            reviewer_action = ""


        # ========================================
        # GET LOAN REQUEST
        # ========================================

        loan_request = (

            state.get(
                "loan_request"
            )

            or

            state.get(
                "loan_application",
                {}
            ).get(
                "loan_request",
                {}
            )

            or

            state.get(
                "loan_application",
                {}
            )

            or

            {}
        )


        # ========================================
        # GET ORIGINAL LOAN AMOUNT
        # ========================================

        requested_loan = (

            loan_request.get(
                "requested_amount"
            )

            or

            loan_request.get(
                "loan_amount"
            )

            or

            loan_request.get(
                "requested_loan_amount"
            )

            or

            state.get(
                "loan_application",
                {}
            ).get(
                "loan_amount"
            )

            or

            state.get(
                "loan_application",
                {}
            ).get(
                "requested_amount"
            )

            or

            0
        )


        # ========================================
        # GET ORIGINAL TENURE
        # ========================================

        tenure_years = (

            loan_request.get(
                "tenure_years"
            )

            or

            loan_request.get(
                "loan_tenure_years"
            )

            or

            loan_request.get(
                "tenure"
            )

            or

            state.get(
                "loan_application",
                {}
            ).get(
                "tenure_years"
            )

            or

            20
        )


        # ========================================
        # NORMALIZE LOAN VALUES
        # ========================================

        try:

            requested_loan = float(
                requested_loan
            )

        except:

            requested_loan = 0.0


        try:

            tenure_years = float(
                tenure_years
            )

        except:

            tenure_years = 20.0


        # ========================================
        # GET NET MONTHLY INCOME
        # ========================================

        net_monthly_income = (

            income.get(
                "net_monthly_income"
            )

            or

            income.get(
                "net_income"
            )

            or

            0
        )


        try:

            net_monthly_income = float(
                net_monthly_income
            )

        except:

            net_monthly_income = 0.0


        # ========================================
        # GET EXISTING EMI
        # ========================================

        existing_emi = (

            liabilities.get(
                "existing_monthly_emi"
            )

            or

            liabilities.get(
                "existing_emi"
            )

            or

            0
        )


        try:

            existing_emi = float(
                existing_emi
            )

        except:

            existing_emi = 0.0


        # ========================================
        # GET UNDERWRITING CHECKS
        # ========================================

        underwriting_checks = (

            underwriting_result.get(
                "checks",
                {}
            )

            or

            {}
        )


        income_eligibility_result = (

            underwriting_checks.get(
                "income_based_eligibility",
                {}
            )

            or

            {}
        )


        estimated_maximum_loan = (

            income_eligibility_result.get(
                "estimated_maximum_loan"
            )

            or

            0
        )


        try:

            estimated_maximum_loan = float(
                estimated_maximum_loan
            )

        except:

            estimated_maximum_loan = 0.0


        # ========================================
        # FALLBACK: GET MAX LOAN FROM
        # UNDERWRITING RECOMMENDATIONS
        # ========================================

        if estimated_maximum_loan <= 0:

            underwriting_recommendations = state.get(
                "underwriting_recommendations",
                {}
            )


            if isinstance(
                underwriting_recommendations,
                dict
            ):

                estimated_maximum_loan = (

                    underwriting_recommendations.get(
                        "estimated_maximum_loan"
                    )

                    or

                    0
                )


                try:

                    estimated_maximum_loan = float(
                        estimated_maximum_loan
                    )

                except:

                    estimated_maximum_loan = 0.0


        # ========================================
        # GET INTEREST RATE
        # ========================================

        interest_rate = (

            loan_request.get(
                "interest_rate"
            )

            or

            loan_request.get(
                "annual_interest_rate"
            )

            or

            state.get(
                "loan_application",
                {}
            ).get(
                "interest_rate"
            )

            or

            8.5
        )


        try:

            interest_rate = float(
                interest_rate
            )

        except:

            interest_rate = 8.5


        # ========================================
        # DEFAULT VALUES
        # ========================================

        restructuring_required = False


        restructured_loan_amount = (
            requested_loan
        )


        restructured_tenure_years = (
            tenure_years
        )


        restructuring_reason = None


        # ========================================
        # VALIDATE REQUIRED DATA
        # ========================================

        missing_required_data = []


        if requested_loan <= 0:

            missing_required_data.append(
                "REQUESTED_LOAN_AMOUNT"
            )


        if net_monthly_income <= 0:

            missing_required_data.append(
                "NET_MONTHLY_INCOME"
            )


        if estimated_maximum_loan <= 0:

            missing_required_data.append(
                "ESTIMATED_MAXIMUM_LOAN"
            )


        # ========================================
        # HANDLE RESTRUCTURE ACTION
        # ========================================

        if (

            reviewer_action
            == "RESTRUCTURE_LOAN"

            and

            not missing_required_data

        ):

            restructuring_required = True


            # ------------------------------------
            # REDUCE LOAN TO ELIGIBLE AMOUNT
            # ------------------------------------

            restructured_loan_amount = min(

                requested_loan,

                estimated_maximum_loan

            )


            restructuring_reason = (
                "Loan amount adjusted to align "
                "with income-based eligibility."
            )


        # ========================================
        # EMI CALCULATION FUNCTION
        # ========================================

        def calculate_emi(

            principal,

            annual_rate,

            tenure_in_years

        ):

            monthly_rate = (
                annual_rate
                / 12
                / 100
            )


            total_months = int(
                tenure_in_years * 12
            )


            if (

                principal <= 0

                or

                total_months <= 0

            ):

                return 0.0


            if monthly_rate == 0:

                return (
                    principal
                    / total_months
                )


            return (

                principal

                * monthly_rate

                * (
                    (1 + monthly_rate)
                    ** total_months
                )

                /

                (
                    (
                        (1 + monthly_rate)
                        ** total_months
                    )

                    - 1
                )

            )


        # ========================================
        # INITIAL EMI CALCULATION
        # ========================================

        recalculated_emi = calculate_emi(

            restructured_loan_amount,

            interest_rate,

            restructured_tenure_years

        )


        # ========================================
        # CALCULATE FOIR
        # ========================================

        if net_monthly_income > 0:

            recalculated_foir = (

                (
                    existing_emi
                    + recalculated_emi
                )

                / net_monthly_income

            ) * 100


        else:

            recalculated_foir = 100.0


        maximum_allowed_foir = 50.0


        foir_pass = (

            recalculated_foir
            <= maximum_allowed_foir

        )


        # ========================================
        # EXTEND TENURE IF REQUIRED
        # ========================================

        if (

            reviewer_action
            == "RESTRUCTURE_LOAN"

            and

            restructuring_required

            and

            not foir_pass

        ):


            maximum_tenure_years = 30


            while (

                restructured_tenure_years
                < maximum_tenure_years

                and

                not foir_pass

            ):


                restructured_tenure_years += 1


                recalculated_emi = calculate_emi(

                    restructured_loan_amount,

                    interest_rate,

                    restructured_tenure_years

                )


                recalculated_foir = (

                    (
                        existing_emi
                        + recalculated_emi
                    )

                    / net_monthly_income

                ) * 100


                foir_pass = (

                    recalculated_foir
                    <= maximum_allowed_foir

                )


            if foir_pass:

                restructuring_reason = (

                    "Loan amount and tenure adjusted "
                    "to satisfy income eligibility "
                    "and FOIR requirements."

                )


        # ========================================
        # INCOME ELIGIBILITY CHECK
        # ========================================

        income_eligibility_pass = (

            restructured_loan_amount > 0

            and

            estimated_maximum_loan > 0

            and

            restructured_loan_amount
            <= estimated_maximum_loan

        )


        # ========================================
        # REASSESS RISK
        # ========================================

        previous_risk_score = (

            risk_assessment.get(
                "risk_score"
            )

            or

            final_system_decision.get(
                "risk_score"
            )

            or

            0
        )


        try:

            previous_risk_score = int(
                previous_risk_score
            )

        except:

            previous_risk_score = 0


        updated_risk_score = (
            previous_risk_score
        )


        # Only reduce risk when restructuring
        # actually resolved the issue

        if restructuring_required:

            if foir_pass:

                updated_risk_score = max(

                    0,

                    updated_risk_score - 20

                )


            if income_eligibility_pass:

                updated_risk_score = max(

                    0,

                    updated_risk_score - 20

                )


        # ========================================
        # UPDATED RISK LEVEL
        # ========================================

        if updated_risk_score >= 70:

            updated_risk_level = "HIGH"


        elif updated_risk_score >= 40:

            updated_risk_level = "MEDIUM"


        else:

            updated_risk_level = "LOW"


        # ========================================
        # GET VERIFICATION STATUS
        # ========================================

        verification_summary = (

            verification_results.get(
                "summary",
                {}
            )

            or

            {}
        )


        verification_status = (

            verification_summary.get(
                "overall_status"
            )

            or

            final_system_decision.get(
                "verification_status"
            )

            or

            "UNKNOWN"
        )


        # ========================================
        # DETERMINE FINAL DECISION
        # ========================================

        final_decision = None

        application_status = None

        case_status = None

        routing = None

        final_decision_reasons = []


        # ----------------------------------------
        # CASE 1
        # REQUIRED DATA MISSING
        # ----------------------------------------

        if missing_required_data:


            final_decision = (
                "ESCALATE_TO_HUMAN_REVIEW"
            )


            application_status = (
                "PENDING_HUMAN_REVIEW"
            )


            case_status = "OPEN"


            routing = (
                "LOAN_REVIEW_TEAM"
            )


            final_decision_reasons.append(

                "Restructuring could not be "
                "completed because required data "
                "is missing."

            )


            final_decision_reasons.append(

                "Missing data: "
                + ", ".join(
                    missing_required_data
                )

            )


        # ----------------------------------------
        # CASE 2
        # RESTRUCTURING SUCCESSFUL
        # ----------------------------------------

        elif (

            reviewer_action
            == "RESTRUCTURE_LOAN"

            and

            restructuring_required

            and

            restructured_loan_amount > 0

            and

            foir_pass

            and

            income_eligibility_pass

        ):


            final_decision = (
                "APPROVED_WITH_RESTRUCTURING"
            )


            application_status = (
                "APPROVED"
            )


            case_status = (
                "CLOSED"
            )


            routing = (
                "LOAN_APPROVAL_PROCESSING"
            )


            final_decision_reasons.append(

                "Loan restructuring resolved "
                "income eligibility and FOIR "
                "requirements."

            )


            final_decision_reasons.append(

                f"Original loan amount: "
                f"₹{round(requested_loan, 2)}."

            )


            final_decision_reasons.append(

                f"Restructured loan amount: "
                f"₹{round(restructured_loan_amount, 2)}."

            )


            final_decision_reasons.append(

                f"Recalculated EMI: "
                f"₹{round(recalculated_emi, 2)}."

            )


            final_decision_reasons.append(

                f"Recalculated FOIR: "
                f"{round(recalculated_foir, 2)}%."

            )


        # ----------------------------------------
        # CASE 3
        # RESTRUCTURING STILL REQUIRED
        # ----------------------------------------

        elif reviewer_action == "RESTRUCTURE_LOAN":


            final_decision = (
                "LOAN_RESTRUCTURING_REQUIRED"
            )


            application_status = (
                "PENDING_RESTRUCTURED_LOAN"
            )


            case_status = (
                "RESTRUCTURING_IN_PROGRESS"
            )


            routing = (
                "LOAN_RESTRUCTURING_TEAM"
            )


            if not foir_pass:

                final_decision_reasons.append(

                    f"FOIR remains above "
                    f"policy limit: "
                    f"{round(recalculated_foir, 2)}%."

                )


            if not income_eligibility_pass:

                final_decision_reasons.append(

                    "Restructured loan amount "
                    "still exceeds income-based "
                    "eligibility."

                )


        # ----------------------------------------
        # CASE 4
        # OTHER REVIEW ACTION
        # ----------------------------------------

        else:


            final_decision = (
                "ESCALATE_TO_HUMAN_REVIEW"
            )


            application_status = (
                "PENDING_HUMAN_REVIEW"
            )


            case_status = (
                "OPEN"
            )


            routing = (
                "LOAN_REVIEW_TEAM"
            )


            final_decision_reasons.append(

                "No supported automatic "
                "restructuring action was found."

            )


        # ========================================
        # BUILD FINAL RESULT
        # ========================================

        restructuring_result = {


            # ------------------------------------
            # PROCESSING STATUS
            # ------------------------------------

            "restructuring_processed":

                True,


            "reviewer_action":

                reviewer_action,


            "restructuring_required":

                restructuring_required,


            # ------------------------------------
            # ORIGINAL LOAN
            # ------------------------------------

            "original_loan_amount":

                round(
                    requested_loan,
                    2
                ),


            "original_tenure_years":

                tenure_years,


            # ------------------------------------
            # RESTRUCTURED LOAN
            # ------------------------------------

            "restructured_loan_amount":

                round(
                    restructured_loan_amount,
                    2
                ),


            "restructured_tenure_years":

                restructured_tenure_years,


            "restructuring_reason":

                restructuring_reason,


            # ------------------------------------
            # CALCULATIONS
            # ------------------------------------

            "interest_rate":

                interest_rate,


            "recalculated_emi":

                round(
                    recalculated_emi,
                    2
                ),


            "existing_emi":

                existing_emi,


            "recalculated_foir":

                round(
                    recalculated_foir,
                    2
                ),


            "maximum_allowed_foir":

                maximum_allowed_foir,


            # ------------------------------------
            # REASSESSMENT
            # ------------------------------------

            "foir_check":

                "PASS"
                if foir_pass
                else "FAIL",


            "income_eligibility_check":

                "PASS"
                if income_eligibility_pass
                else "FAIL",


            "estimated_maximum_loan":

                round(
                    estimated_maximum_loan,
                    2
                ),


            # ------------------------------------
            # RISK
            # ------------------------------------

            "previous_risk_score":

                previous_risk_score,


            "updated_risk_score":

                updated_risk_score,


            "updated_risk_level":

                updated_risk_level,


            # ------------------------------------
            # FINAL RESOLUTION
            # ------------------------------------

            "final_decision":

                final_decision,


            "application_status":

                application_status,


            "case_status":

                case_status,


            "routing":

                routing,


            "final_decision_reasons":

                final_decision_reasons


        }


        # ========================================
        # SAVE RESULTS
        # ========================================

        state[
            "loan_restructuring_result"
        ] = restructuring_result


        state[
            "application_status"
        ] = application_status


        # ========================================
        # LOG RESULT
        # ========================================

        self.log(
            state,
            "COMPLETED",
            f"Final Decision: {final_decision} | "
            f"Original Amount: "
            f"₹{round(requested_loan, 2)} | "
            f"Restructured Amount: "
            f"₹{round(restructured_loan_amount, 2)} | "
            f"FOIR: "
            f"{round(recalculated_foir, 2)}%"
        )


        return state


print(
    "✅ Updated LoanRestructuringReassessmentAgent loaded"
)

# ===== NOTEBOOK CELL 33 =====
# ========================================
# INITIALIZE ALL 11 AGENTS
# RUN AFTER ALL AGENT CLASS CELLS
# ========================================

print("🚀 Initializing all 11 agents...")


# ----------------------------------------
# AGENT 1 - DOCUMENT INTAKE
# ----------------------------------------

agent_1 = DocumentIntakeAgent()

print("✅ Agent 1 - DocumentIntakeAgent ready")


# ----------------------------------------
# AGENT 2 - DOCUMENT CHECKLIST
# ----------------------------------------

agent_2 = DocumentChecklistAgent()

print("✅ Agent 2 - DocumentChecklistAgent ready")


# ----------------------------------------
# AGENT 3 - DOCUMENT INTELLIGENCE
# ----------------------------------------

agent_3 = DocumentIntelligenceAgent()

print("✅ Agent 3 - DocumentIntelligenceAgent ready")


# ----------------------------------------
# AGENT 4 - CROSS DOCUMENT VERIFICATION
# ----------------------------------------

agent_4 = CrossDocumentVerificationAgent()

print("✅ Agent 4 - CrossDocumentVerificationAgent ready")


# ----------------------------------------
# AGENT 5 - LOAN ELIGIBILITY & UNDERWRITING
# ----------------------------------------

agent_5 = LoanEligibilityUnderwritingAgent()

print("✅ Agent 5 - LoanEligibilityUnderwritingAgent ready")


# ----------------------------------------
# AGENT 6 - RISK, FRAUD & EXCEPTION
# ----------------------------------------

agent_6 = RiskFraudExceptionAgent()

print("✅ Agent 6 - RiskFraudExceptionAgent ready")


# ----------------------------------------
# AGENT 7 - LOAN CASE SUMMARY
# ----------------------------------------

agent_7 = LoanCaseSummaryAgent()

print("✅ Agent 7 - LoanCaseSummaryAgent ready")


# ----------------------------------------
# AGENT 8 - FINAL LOAN DECISION
# ----------------------------------------

agent_8 = FinalLoanDecisionAgent()

print("✅ Agent 8 - FinalLoanDecisionAgent ready")


# ----------------------------------------
# AGENT 9 - HUMAN REVIEW CASE MANAGEMENT
# ----------------------------------------

agent_9 = HumanReviewCaseManagementAgent()

print("✅ Agent 9 - HumanReviewCaseManagementAgent ready")


# ----------------------------------------
# AGENT 10 - HUMAN REVIEWER DECISION
# ----------------------------------------

agent_10 = HumanReviewerDecisionAgent()

print("✅ Agent 10 - HumanReviewerDecisionAgent ready")


# ----------------------------------------
# AGENT 11 - LOAN RESTRUCTURING & REASSESSMENT
# ----------------------------------------

agent_11 = LoanRestructuringReassessmentAgent()

print("✅ Agent 11 - LoanRestructuringReassessmentAgent ready")


print("\n" + "=" * 60)
print("🎉 ALL 11 AGENTS INITIALIZED SUCCESSFULLY")
print("=" * 60)

# ===== NOTEBOOK CELL 34 =====
# ========================================
# GRADIO LOAN PROCESSING PIPELINE
# RUNS AGENTS 1 TO 9
# SUPPORTS OPTIONAL DOCUMENT UPLOADS
# ========================================

import json
import os


# ========================================
# DOCUMENT CONTENT EXTRACTION
# ========================================

def extract_document_content(file_path):

    if not file_path:
        return ""

    try:

        file_extension = os.path.splitext(
            file_path
        )[1].lower()


        # ====================================
        # TEXT / MARKDOWN
        # ====================================

        if file_extension in [".txt", ".md"]:

            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                return file.read()


        # ====================================
        # JSON
        # ====================================

        elif file_extension == ".json":

            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                data = json.load(file)

            return json.dumps(
                data,
                indent=2
            )


        # ====================================
        # CSV
        # ====================================

        elif file_extension == ".csv":

            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                return file.read()


        # ====================================
        # PDF
        # ====================================

        elif file_extension == ".pdf":

            try:

                from pypdf import PdfReader

                reader = PdfReader(
                    file_path
                )

                content = []

                for page in reader.pages:

                    page_text = (
                        page.extract_text()
                        or ""
                    )

                    content.append(
                        page_text
                    )

                return "\n".join(
                    content
                )

            except Exception as pdf_error:

                print(
                    f"⚠️ PDF extraction failed: "
                    f"{pdf_error}"
                )

                return ""


        # ====================================
        # DOCX
        # ====================================

        elif file_extension == ".docx":

            try:

                from docx import Document

                document = Document(
                    file_path
                )

                return "\n".join(
                    paragraph.text
                    for paragraph
                    in document.paragraphs
                )

            except Exception as docx_error:

                print(
                    f"⚠️ DOCX extraction failed: "
                    f"{docx_error}"
                )

                return ""


        # ====================================
        # UNSUPPORTED FILE
        # ====================================

        else:

            print(
                f"⚠️ Unsupported file type: "
                f"{file_extension}"
            )

            return ""


    except Exception as error:

        print(
            f"⚠️ Document extraction error: "
            f"{error}"
        )

        return ""



# ========================================
# NORMALIZE DOCUMENT CHECKLIST
# ========================================

def normalize_document_checklist(loan_state):

    document_inventory = loan_state.get(
        "document_inventory",
        {}
    )


    if not isinstance(
        document_inventory,
        dict
    ):

        document_inventory = {
            "submitted": [],
            "required": [],
            "missing": [],
            "satisfied": []
        }


    loan_state[
        "document_checklist"
    ] = {

        "required_documents":
            document_inventory.get(
                "required",
                []
            ),

        "missing_documents":
            document_inventory.get(
                "missing",
                []
            ),

        "satisfied_documents":
            document_inventory.get(
                "satisfied",
                []
            )
    }


    return loan_state



# ========================================
# MAIN LOAN APPLICATION PIPELINE
# ========================================

def run_loan_application(

    full_name,
    date_of_birth,
    pan,
    mobile,
    email,
    address,
    employer,
    years_of_experience,
    current_employment_years,
    gross_monthly_income,
    net_monthly_income,
    existing_monthly_emi,
    requested_loan_amount,
    loan_tenure_years,
    interest_rate,
    loan_purpose,
    property_value,
    uploaded_files

):

    try:


        # ====================================
        # PREPARE UPLOADED DOCUMENTS
        # ====================================

        documents = []


        if uploaded_files:


            # Handle a single file
            if isinstance(
                uploaded_files,
                str
            ):

                uploaded_files = [
                    uploaded_files
                ]


            for index, file_path in enumerate(
                uploaded_files
            ):

                try:

                    if not file_path:
                        continue


                    file_name = os.path.basename(
                        file_path
                    )


                    print(
                        f"\n📄 Processing: "
                        f"{file_name}"
                    )


                    document_content = (
                        extract_document_content(
                            file_path
                        )
                    )


                    documents.append({

                        "document_id":
                            f"DOC-{index + 1:03d}",

                        "file_name":
                            file_name,

                        "file_path":
                            file_path,

                        "content":
                            document_content

                    })


                    print(
                        f"✅ Loaded: "
                        f"{file_name}"
                    )

                    print(
                        f"   Content length: "
                        f"{len(document_content)}"
                    )


                except Exception as document_error:

                    print(
                        f"⚠️ Failed to process "
                        f"document: "
                        f"{document_error}"
                    )


        else:

            print(
                "\n⚠️ No documents uploaded."
            )

            print(
                "Pipeline will continue "
                "without documents."
            )



        # ====================================
        # CREATE INITIAL LOAN STATE
        # ====================================

        loan_state = {


            # ================================
            # APPLICATION
            # ================================

            "application_id":
                "HL-2026-0001",


            # ================================
            # APPLICANTS
            # ================================

            "applicants": [

                {

                    "applicant_id":
                        "APPLICANT-001",

                    "role":
                        "PRIMARY_APPLICANT",


                    "personal_details": {

                        "full_name":
                            full_name,

                        "date_of_birth":
                            str(
                                date_of_birth
                            ),

                        "pan":
                            pan,

                        "mobile":
                            mobile,

                        "email":
                            email,

                        "address":
                            address
                    },


                    "employment": {

                        "employment_type":
                            "SALARIED",

                        "employer_or_business":
                            employer,

                        "years_of_experience":
                            int(
                                years_of_experience
                                or 0
                            ),

                        "current_employment_years":
                            int(
                                current_employment_years
                                or 0
                            )
                    },


                    "income": {

                        "gross_monthly_income":
                            float(
                                gross_monthly_income
                                or 0
                            ),

                        "net_monthly_income":
                            float(
                                net_monthly_income
                                or 0
                            ),

                        "average_bank_salary_credit":
                            float(
                                net_monthly_income
                                or 0
                            ),

                        "annual_itr_income":
                            None
                    },


                    "liabilities": {

                        "existing_monthly_emi":
                            float(
                                existing_monthly_emi
                                or 0
                            )
                    },


                    "credit": {

                        "credit_score":
                            None,

                        "credit_report_status":
                            None
                    }

                }

            ],


            # ================================
            # LOAN REQUEST
            # ================================

            "loan_request": {

                "requested_amount":
                    float(
                        requested_loan_amount
                        or 0
                    ),

                "requested_loan_amount":
                    float(
                        requested_loan_amount
                        or 0
                    ),

                "tenure_years":
                    float(
                        loan_tenure_years
                        or 0
                    ),

                "requested_tenure_years":
                    float(
                        loan_tenure_years
                        or 0
                    ),

                "interest_rate":
                    float(
                        interest_rate
                        or 0
                    ),

                "purpose":
                    loan_purpose

            },


            # ================================
            # PROPERTY
            # ================================

            "property": {

                "property_value":
                    float(
                        property_value
                        or 0
                    ),

                "valuation_value":
                    float(
                        property_value
                        or 0
                    ),

                "market_value":
                    float(
                        property_value
                        or 0
                    )

            },


            # ================================
            # DOCUMENTS
            # ================================

            "documents":
                documents,


            # ================================
            # DOCUMENT INVENTORY
            # ================================

            "document_inventory": {

                "submitted": [],

                "required": [],

                "missing": [],

                "satisfied": []

            },


            # ================================
            # DOCUMENT CHECKLIST
            # ================================

            "document_checklist": {

                "required_documents": [],

                "missing_documents": [],

                "satisfied_documents": []

            },


            # ================================
            # AGENT OUTPUTS
            # ================================

            "extracted_data": {

                "documents": []

            },

            "verification_results": {},

            "underwriting_result": {},

            "risk_assessment": {},

            "ai_case_summary": {},

            "final_decision": {},

            "human_review_case": {},

            "human_review_queue": [],

            "agent_logs": []

        }



        # ====================================
        # PIPELINE START
        # ====================================

        print("\n")
        print("=" * 70)
        print(
            "🚀 STARTING LOAN "
            "PROCESSING PIPELINE"
        )
        print("=" * 70)

        print(
            f"Application ID: "
            f"{loan_state['application_id']}"
        )

        print(
            f"Documents uploaded: "
            f"{len(documents)}"
        )



        # ====================================
        # AGENT 1
        # DOCUMENT INTAKE & CLASSIFICATION
        # ====================================

        print("\n")
        print("=" * 70)
        print(
            "▶ AGENT 1: "
            "DocumentIntakeAgent"
        )
        print("=" * 70)


        result = agent_1.run(
            loan_state
        )


        if not isinstance(
            result,
            dict
        ):

            raise TypeError(
                "Agent 1 did not return "
                "a valid state dictionary."
            )


        loan_state = result

        print(
            "✅ Agent 1 completed"
        )



        # ====================================
        # AGENT 2
        # DOCUMENT CHECKLIST
        # ====================================

        print("\n")
        print("=" * 70)
        print(
            "▶ AGENT 2: "
            "DocumentChecklistAgent"
        )
        print("=" * 70)


        result = agent_2.run(
            loan_state
        )


        if not isinstance(
            result,
            dict
        ):

            raise TypeError(
                "Agent 2 did not return "
                "a valid state dictionary."
            )


        loan_state = result

        print(
            "✅ Agent 2 completed"
        )



        # ====================================
        # NORMALIZE AGENT 2 OUTPUT
        # MUST HAPPEN BEFORE AGENT 3-9
        # ====================================

        loan_state = (
            normalize_document_checklist(
                loan_state
            )
        )


        print(
            "📋 Document checklist normalized"
        )



        # ====================================
        # AGENT 3
        # DOCUMENT INTELLIGENCE
        # ====================================

        print("\n")
        print("=" * 70)
        print(
            "▶ AGENT 3: "
            "DocumentIntelligenceAgent"
        )
        print("=" * 70)


        loan_state = agent_3.run(
            loan_state
        )


        # ====================================
        # AGENT 4
        # CROSS-DOCUMENT VERIFICATION
        # ====================================

        print("\n")
        print("=" * 70)
        print(
            "▶ AGENT 4: "
            "CrossDocumentVerificationAgent"
        )
        print("=" * 70)


        loan_state = agent_4.run(
            loan_state
        )


        # ====================================
        # AGENT 5
        # LOAN ELIGIBILITY & UNDERWRITING
        # ====================================

        print("\n")
        print("=" * 70)
        print(
            "▶ AGENT 5: "
            "LoanEligibilityUnderwritingAgent"
        )
        print("=" * 70)


        loan_state = agent_5.run(
            loan_state
        )


        # ====================================
        # AGENT 6
        # RISK, FRAUD & EXCEPTION DETECTION
        # ====================================

        print("\n")
        print("=" * 70)
        print(
            "▶ AGENT 6: "
            "RiskFraudExceptionAgent"
        )
        print("=" * 70)


        loan_state = agent_6.run(
            loan_state
        )


        # ====================================
        # AGENT 7
        # AI CASE SUMMARY
        # ====================================

        print("\n")
        print("=" * 70)
        print(
            "▶ AGENT 7: "
            "LoanCaseSummaryAgent"
        )
        print("=" * 70)


        loan_state = agent_7.run(
            loan_state
        )


        # ====================================
        # AGENT 8
        # FINAL LOAN DECISION
        # ====================================

        print("\n")
        print("=" * 70)
        print(
            "▶ AGENT 8: "
            "FinalLoanDecisionAgent"
        )
        print("=" * 70)


        loan_state = agent_8.run(
            loan_state
        )


        # ====================================
        # AGENT 9
        # HUMAN REVIEW CASE MANAGEMENT
        # ====================================

        print("\n")
        print("=" * 70)
        print(
            "▶ AGENT 9: "
            "HumanReviewCaseManagementAgent"
        )
        print("=" * 70)


        loan_state = agent_9.run(
            loan_state
        )


        # ====================================
        # AGENT 10
        # HUMAN REVIEWER DECISION & RESOLUTION
        # ====================================

        print("\n")
        print("=" * 70)
        print("▶ AGENT 10: HumanReviewerDecisionAgent")
        print("=" * 70)

        loan_state = agent_10.run(
            loan_state
        )


        # ====================================
        # AGENT 11
        # LOAN RESTRUCTURING, REASSESSMENT
        # & FINAL RESOLUTION
        # ====================================

        print("\n")
        print("=" * 70)
        print("▶ AGENT 11: LoanRestructuringReassessmentAgent")
        print("=" * 70)

        loan_state = agent_11.run(
            loan_state
        )



        # ====================================
        # FINAL CHECKLIST NORMALIZATION
        # ====================================

        loan_state = (
            normalize_document_checklist(
                loan_state
            )
        )



        # ====================================
        # GET RESULTS
        # ====================================

        verification = (
            loan_state.get(
                "verification_results",
                {}
            )
        )


        underwriting = (
            loan_state.get(
                "underwriting_result",
                {}
            )
        )


        risk = (
            loan_state.get(
                "risk_assessment",
                {}
            )
        )


        ai_summary = (
            loan_state.get(
                "ai_case_summary",
                {}
            )
        )


        final_decision = (
            loan_state.get(
                "final_decision",
                {}
            )
        )


        human_review = (
            loan_state.get(
                "human_review_case",
                {}
            )
        )



        # ====================================
        # CREATE FINAL RESULT
        # ====================================

        # ====================================
        # CREATE FINAL RESULT
        # IMPORTANT:
        # Keep the original application data AND all important
        # agent outputs in the final result. The PDF/report layer
        # receives this object, so it must never depend only on
        # AI-generated summaries for numeric application values.
        # ====================================

        primary_applicant = (
            loan_state.get("applicants", [{}])[0]
            if loan_state.get("applicants")
            else {}
        )

        personal_details = primary_applicant.get(
            "personal_details", {}
        ) if isinstance(primary_applicant, dict) else {}

        employment_details = primary_applicant.get(
            "employment", {}
        ) if isinstance(primary_applicant, dict) else {}

        income_details = primary_applicant.get(
            "income", {}
        ) if isinstance(primary_applicant, dict) else {}

        liability_details = primary_applicant.get(
            "liabilities", {}
        ) if isinstance(primary_applicant, dict) else {}

        loan_request_data = loan_state.get(
            "loan_request", {}
        )
        if not isinstance(loan_request_data, dict):
            loan_request_data = {}

        property_data = loan_state.get(
            "property", {}
        )
        if not isinstance(property_data, dict):
            property_data = {}

        final_result = {
            "status": "SUCCESS",
            "application_id": loan_state.get("application_id"),

            # Original application data - authoritative source
            "applicant_name": personal_details.get("full_name", full_name),
            "date_of_birth": personal_details.get("date_of_birth", str(date_of_birth)),
            "pan": personal_details.get("pan", pan),
            "mobile": personal_details.get("mobile", mobile),
            "email": personal_details.get("email", email),
            "applicant_address": personal_details.get("address", address),
            "employer": employment_details.get("employer_or_business", employer),
            "years_of_experience": employment_details.get("years_of_experience", years_of_experience),
            "current_employment_years": employment_details.get("current_employment_years", current_employment_years),
            "gross_monthly_income": income_details.get("gross_monthly_income", gross_monthly_income),
            "net_monthly_income": income_details.get("net_monthly_income", net_monthly_income),
            "existing_monthly_emi": liability_details.get("existing_monthly_emi", existing_monthly_emi),
            "requested_loan_amount": loan_request_data.get("requested_amount", requested_loan_amount),
            "loan_tenure_years": loan_request_data.get("tenure_years", loan_tenure_years),
            "interest_rate": loan_request_data.get("interest_rate", interest_rate),
            "loan_purpose": loan_request_data.get("purpose", loan_purpose),
            "property_value": property_data.get("property_value", property_value),

            # Full source structures for report/PDF and downstream UI
            "applicant": primary_applicant,
            "loan_request": loan_request_data,
            "property": property_data,

            "documents_uploaded": len(loan_state.get("documents", [])),
            "document_checklist": loan_state.get("document_checklist", {}),

            # Agent outputs
            "verification": verification.get("summary", verification),
            "verification_details": verification,
            "underwriting": underwriting,
            "underwriting_details": underwriting,
            "risk": risk,
            "final_decision": final_decision,
            "ai_summary": ai_summary,
            "human_review": human_review,
            "reviewer_resolution": loan_state.get("reviewer_resolution", {}),
            "loan_restructuring": loan_state.get("loan_restructuring_result", {}),
            "application_status": loan_state.get("application_status", ""),

            # Complete state snapshot makes report generation independent
            # from any one agent's summary schema.
            "loan_state_snapshot": loan_state
        }


        # ====================================
        # PIPELINE COMPLETE
        # ====================================

        print("\n")
        print("=" * 70)
        print(
            "🎉 LOAN PROCESSING "
            "PIPELINE COMPLETED"
        )
        print("=" * 70)



        return (
            final_result,
            loan_state
        )



    except Exception as error:

        import traceback

        print("\n")
        print("=" * 70)
        print("❌ PIPELINE ERROR")
        print("=" * 70)

        traceback.print_exc()


        error_result = {

            "status":
                "ERROR",

            "message":
                str(error)

        }


        return (
            error_result,
            {}
        )


print(
    "✅ Complete loan processing "
    "pipeline loaded successfully"
)

# ===== NOTEBOOK CELL 35 =====
# ========================================
# LOAN APPLICATION + PDF REPORT FUNCTION
# UPDATED VERSION
# ========================================


import os
import html
import json
import base64

from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)


# ========================================
# FORMAT VALUE
# ========================================

def format_value(value):

    if value is None:
        return "Not Available"

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, float):
        return f"{value:,.2f}"

    if isinstance(value, int):
        return f"{value:,}"

    if isinstance(value, list):

        if not value:
            return "None"

        return ", ".join(
            str(item)
            for item in value
        )

    return str(value)


# ========================================
# FORMAT CURRENCY
# ========================================

def format_currency(value):

    if value is None:
        return "Not Available"

    try:

        value = float(value)

        return f"₹{value:,.2f}"

    except Exception:

        return str(value)


# ========================================
# BUILD DECISION-BASED EXECUTIVE SUMMARY
# ========================================

def build_decision_based_executive_summary(result):

    final_decision = result.get(
        "final_decision",
        {}
    )

    underwriting = result.get(
        "underwriting",
        {}
    )

    risk = result.get(
        "risk",
        {}
    )

    verification = result.get(
        "verification",
        {}
    )

    document_checklist = result.get(
        "document_checklist",
        {}
    )

    ai_summary = result.get(
        "ai_summary",
        {}
    )


    # ====================================
    # APPLICATION
    # ====================================

    application_id = result.get(
        "application_id",
        "Not Available"
    )


    # ====================================
    # APPLICANT
    # ====================================

    applicant_profile = ai_summary.get(
        "applicant_profile",
        {}
    )
    if not isinstance(applicant_profile, dict):
        applicant_profile = {}

    applicant_name = (
        applicant_profile.get("name")
        or result.get("applicant_name")
        or "Applicant"
    )


    # ====================================
    # LOAN REQUEST
    # ====================================

    loan_request_summary = ai_summary.get(
        "loan_request_summary",
        {}
    )

    requested_amount = (
        loan_request_summary.get("requested_amount")
        or result.get("requested_loan_amount")
        or result.get("loan_request", {}).get("requested_amount", 0)
    )

    tenure_years = (
        loan_request_summary.get("tenure_years")
        or result.get("loan_tenure_years")
        or result.get("loan_request", {}).get("tenure_years", 0)
    )

    loan_purpose = (
        loan_request_summary.get("purpose")
        or result.get("loan_purpose")
        or result.get("loan_request", {}).get("purpose")
        or "HOME LOAN"
    )


    # ====================================
    # ACTUAL FINAL DECISION
    # ====================================

    actual_final_decision = final_decision.get(
        "final_decision",
        "PENDING"
    )


    routing = final_decision.get(
        "routing",
        "NOT_ASSIGNED"
    )


    # ====================================
    # UNDERWRITING
    # ====================================

    underwriting_decision = underwriting.get(
        "decision",
        final_decision.get(
            "underwriting_decision",
            "UNKNOWN"
        )
    )


    # ====================================
    # RISK
    # ====================================

    risk_score = risk.get(
        "risk_score",
        final_decision.get(
            "risk_score",
            0
        )
    )

    risk_level = risk.get(
        "risk_level",
        final_decision.get(
            "risk_level",
            "UNKNOWN"
        )
    )

    human_review_required = risk.get(
        "human_review_required",
        final_decision.get(
            "human_review_required",
            False
        )
    )


    # ====================================
    # VERIFICATION
    # ====================================

    verification_status = verification.get(
        "overall_status",
        final_decision.get(
            "verification_status",
            "UNKNOWN"
        )
    )


    # ====================================
    # FAILED UNDERWRITING CHECKS
    # ====================================

    failed_checks = final_decision.get(
        "failed_underwriting_checks",
        []
    )

    if not failed_checks:

        failed_checks = []

        underwriting_checks = underwriting.get(
            "checks",
            {}
        )

        if isinstance(underwriting_checks, dict):

            for check_name, check_data in underwriting_checks.items():

                if not isinstance(
                    check_data,
                    dict
                ):
                    continue

                if check_data.get(
                    "status"
                ) == "FAIL":

                    failed_checks.append(
                        check_name.upper()
                    )


    # ====================================
    # MISSING DOCUMENTS
    # ====================================

    missing_documents = document_checklist.get(
        "missing_documents",
        []
    )

    missing_document_count = len(
        missing_documents
    )


    # ====================================
    # DECISION SENTENCE
    # ====================================

    if actual_final_decision == "APPROVED":

        decision_sentence = (
            "The loan application has been "
            "approved by the system."
        )

    elif actual_final_decision == "APPROVED_WITH_RESTRUCTURING":

        decision_sentence = (
            "The loan application has been "
            "approved with restructuring."
        )

    elif actual_final_decision == "REJECTED":

        decision_sentence = (
            "The loan application has been "
            "rejected based on the applicable "
            "underwriting and risk criteria."
        )

    elif actual_final_decision == "ESCALATE_TO_HUMAN_REVIEW":

        decision_sentence = (
            "The loan application has not received "
            "a final automated approval or rejection. "
            "The case has been escalated to human "
            "review for further assessment."
        )

    elif actual_final_decision == "REVIEW_REQUIRED":

        decision_sentence = (
            "The loan application requires additional "
            "review before a final decision can be made."
        )

    elif actual_final_decision == "NOT_ELIGIBLE":

        decision_sentence = (
            "The loan application is currently "
            "not eligible under the configured "
            "underwriting criteria."
        )

    else:

        decision_sentence = (
            f"The current system decision is "
            f"{actual_final_decision}."
        )


    # ====================================
    # FAILED CHECKS TEXT
    # ====================================

    failed_check_sentence = ""

    if failed_checks:

        failed_check_sentence = (
            " Failed underwriting checks: "
            + ", ".join(
                failed_checks
            )
            + "."
        )


    # ====================================
    # DOCUMENT TEXT
    # ====================================

    if missing_document_count > 0:

        document_sentence = (
            f" {missing_document_count} required "
            "document(s) are currently missing."
        )

    else:

        document_sentence = (
            " All currently required documents "
            "are available."
        )


    # ====================================
    # HUMAN REVIEW TEXT
    # ====================================

    if human_review_required:

        human_review_sentence = (
            " Human review is required before "
            "the case can proceed to final resolution."
        )

    else:

        human_review_sentence = (
            " Human review is not currently required."
        )


    # ====================================
    # FINAL SUMMARY
    # ====================================

    executive_summary = (

        f"Application {application_id} for "
        f"{applicant_name} requests "
        f"{format_currency(requested_amount)} "
        f"over {format_value(tenure_years)} years "
        f"for {loan_purpose}. "

        f"{decision_sentence} "

        f"Underwriting decision: "
        f"{underwriting_decision}. "

        f"Risk score: "
        f"{format_value(risk_score)}/100, "
        f"risk level: {risk_level}. "

        f"Verification status: "
        f"{verification_status}."

        f"{failed_check_sentence}"

        f"{document_sentence}"

        f"{human_review_sentence}"
    )


    return executive_summary


# ========================================
# CREATE HUMAN READABLE HTML REPORT
# ========================================

def generate_html_report(result):

    application_id = result.get(
        "application_id",
        "Not Available"
    )

    verification = result.get(
        "verification",
        {}
    )

    underwriting = result.get(
        "underwriting",
        {}
    )

    risk = result.get(
        "risk",
        {}
    )

    final_decision = result.get(
        "final_decision",
        {}
    )

    ai_summary = result.get(
        "ai_summary",
        {}
    )

    human_review = result.get(
        "human_review",
        {}
    )

    document_checklist = result.get(
        "document_checklist",
        {}
    )


    # ====================================
    # USE ACTUAL DECISION-BASED SUMMARY
    # ====================================

    executive_summary = (
        build_decision_based_executive_summary(
            result
        )
    )


    decision = final_decision.get(
        "final_decision",
        "PENDING"
    )

    risk_level = risk.get(
        "risk_level",
        "UNKNOWN"
    )

    risk_score = risk.get(
        "risk_score",
        0
    )


    # ====================================
    # HTML REPORT
    # ====================================

    html_report = f"""

    <div style="
        font-family: Arial, sans-serif;
        max-width: 1000px;
        margin: auto;
        padding: 25px;
        background: white;
        color: #222;
    ">

        <div style="
            background: #1f4e78;
            color: white;
            padding: 25px;
            border-radius: 10px;
        ">

            <h1>
                🏦 Loan Processing Report
            </h1>

            <p>
                <b>Application ID:</b>
                {html.escape(
                    str(application_id)
                )}
            </p>

            <p>
                <b>Generated:</b>
                {datetime.now().strftime(
                    "%d %B %Y, %I:%M %p"
                )}
            </p>

        </div>

        <br>

        <h2>🎯 Final Decision</h2>

        <div style="
            padding: 20px;
            border-radius: 10px;
            background: #f5f5f5;
            border-left: 6px solid #1f4e78;
        ">

            <h3>
                {html.escape(
                    str(decision)
                )}
            </h3>

            <p>
                <b>Routing:</b>
                {html.escape(
                    str(
                        final_decision.get(
                            "routing",
                            "Not Available"
                        )
                    )
                )}
            </p>

            <p>
                <b>Human Review Required:</b>
                {format_value(
                    final_decision.get(
                        "human_review_required"
                    )
                )}
            </p>

        </div>

        <br>

        <h2>🤖 Executive Summary</h2>

        <p>
            {html.escape(
                str(executive_summary)
            )}
        </p>

        <br>

        <h2>📎 Document Status</h2>

        <table style="
            width: 100%;
            border-collapse: collapse;
        " border="1" cellpadding="10">

            <tr>
                <th>Documents Uploaded</th>
                <th>Required</th>
                <th>Satisfied</th>
                <th>Missing</th>
            </tr>

            <tr>

                <td>
                    {result.get(
                        "documents_uploaded",
                        0
                    )}
                </td>

                <td>
                    {len(
                        document_checklist.get(
                            "required_documents",
                            []
                        )
                    )}
                </td>

                <td>
                    {len(
                        document_checklist.get(
                            "satisfied_documents",
                            []
                        )
                    )}
                </td>

                <td>
                    {len(
                        document_checklist.get(
                            "missing_documents",
                            []
                        )
                    )}
                </td>

            </tr>

        </table>

        <br>

        <h3>Missing Documents</h3>

        <ul>
    """


    # ====================================
    # MISSING DOCUMENTS
    # ====================================

    missing_documents = document_checklist.get(
        "missing_documents",
        []
    )


    if missing_documents:

        for document in missing_documents:

            html_report += f"""

            <li>
                {html.escape(
                    str(document)
                )}
            </li>

            """

    else:

        html_report += """

        <li>
            No required documents are missing.
        </li>

        """


    html_report += """

        </ul>

        <br>

        <h2>🔎 Verification Results</h2>

        <table style="
            width: 100%;
            border-collapse: collapse;
        " border="1" cellpadding="10">

            <tr>
                <th>Total Checks</th>
                <th>Matches</th>
                <th>Mismatches</th>
                <th>Review Required</th>
                <th>Insufficient Data</th>
            </tr>

            <tr>
    """


    html_report += f"""

                <td>
                    {verification.get(
                        "total_checks",
                        0
                    )}
                </td>

                <td>
                    {verification.get(
                        "matches",
                        0
                    )}
                </td>

                <td>
                    {verification.get(
                        "mismatches",
                        0
                    )}
                </td>

                <td>
                    {verification.get(
                        "review_required",
                        0
                    )}
                </td>

                <td>
                    {verification.get(
                        "insufficient_data",
                        0
                    )}
                </td>

            </tr>

        </table>

        <p>
            <b>Overall Status:</b>
            {html.escape(
                str(
                    verification.get(
                        "overall_status",
                        "UNKNOWN"
                    )
                )
            )}
        </p>

        <br>

        <h2>💰 Underwriting Results</h2>

        <table style="
            width: 100%;
            border-collapse: collapse;
        " border="1" cellpadding="10">

            <tr>
                <th>Total Checks</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Review Required</th>
            </tr>

            <tr>

                <td>
                    {underwriting.get(
                        "total_checks",
                        0
                    )}
                </td>

                <td>
                    {underwriting.get(
                        "passed",
                        0
                    )}
                </td>

                <td>
                    {underwriting.get(
                        "failed",
                        0
                    )}
                </td>

                <td>
                    {underwriting.get(
                        "review_required",
                        0
                    )}
                </td>

            </tr>

        </table>

        <p>
            <b>Underwriting Decision:</b>
            {html.escape(
                str(
                    underwriting.get(
                        "decision",
                        "UNKNOWN"
                    )
                )
            )}
        </p>

        <br>

        <h2>⚠️ Risk Assessment</h2>

        <div style="
            padding: 20px;
            background: #fff3cd;
            border-radius: 10px;
        ">

            <h3>
                Risk Score:
                {format_value(
                    risk_score
                )}
                / 100
            </h3>

            <h3>
                Risk Level:
                {html.escape(
                    str(risk_level)
                )}
            </h3>

            <p>
                <b>Human Review Required:</b>
                {format_value(
                    risk.get(
                        "human_review_required"
                    )
                )}
            </p>

            <p>
                <b>Recommendation:</b>
                {html.escape(
                    str(
                        risk.get(
                            "recommendation",
                            "Not Available"
                        )
                    )
                )}
            </p>

        </div>

        <br>

        <h2>📌 Key Findings</h2>

        <ul>
    """


    key_findings = ai_summary.get(
        "key_findings",
        []
    )


    if key_findings:

        for finding in key_findings:

            html_report += f"""

            <li>
                {html.escape(
                    str(finding)
                )}
            </li>

            """

    else:

        html_report += """

        <li>
            No key findings available.
        </li>

        """


    html_report += """

        </ul>

        <br>

        <h2>✅ Recommended Actions</h2>

        <ol>
    """


    recommended_actions = ai_summary.get(
        "recommended_actions",
        []
    )


    if recommended_actions:

        for action in recommended_actions:

            html_report += f"""

            <li>
                {html.escape(
                    str(action)
                )}
            </li>

            """

    else:

        html_report += """

        <li>
            No recommended actions available.
        </li>

        """


    html_report += """

        </ol>

        <br>

        <h2>👨‍💼 Human Review</h2>

        <table style="
            width: 100%;
            border-collapse: collapse;
        " border="1" cellpadding="10">

            <tr>
                <th>Case Created</th>
                <th>Case ID</th>
                <th>Priority</th>
                <th>Assigned Team</th>
            </tr>

            <tr>

                <td>
                    {human_review.get(
                        "case_created",
                        "Not Available"
                    )}
                </td>

                <td>
                    {html.escape(
                        str(
                            human_review.get(
                                "case_id",
                                "Not Available"
                            )
                        )
                    )}
                </td>

                <td>
                    {html.escape(
                        str(
                            human_review.get(
                                "priority",
                                "Not Available"
                            )
                        )
                    )}
                </td>

                <td>
                    {html.escape(
                        str(
                            human_review.get(
                                "assigned_team",
                                "Not Available"
                            )
                        )
                    )}
                </td>

            </tr>

        </table>

        <br><br>

        <hr>

        <p style="
            text-align:center;
            color:#777;
        ">

            AI Loan Processing System
            <br>
            Generated automatically

        </p>

    </div>
    """


    return html_report


# ========================================
# CREATE PDF REPORT
# ========================================

def generate_loan_pdf(result):

    os.makedirs(
        "loan_reports",
        exist_ok=True
    )


    application_id = result.get(
        "application_id",
        "loan_application"
    )


    safe_application_id = str(
        application_id
    ).replace(
        "/",
        "_"
    ).replace(
        "\\",
        "_"
    )


    pdf_path = os.path.join(
        "loan_reports",
        f"{safe_application_id}_report.pdf"
    )


    doc = SimpleDocTemplate(

        pdf_path,

        pagesize=A4,

        rightMargin=40,

        leftMargin=40,

        topMargin=40,

        bottomMargin=40
    )


    styles = getSampleStyleSheet()


    title_style = ParagraphStyle(

        "LoanTitle",

        parent=styles["Title"],

        alignment=TA_CENTER,

        fontSize=22,

        leading=28,

        textColor=colors.HexColor(
            "#1f4e78"
        )
    )


    heading_style = ParagraphStyle(

        "LoanHeading",

        parent=styles["Heading2"],

        fontSize=15,

        leading=20,

        spaceBefore=15,

        spaceAfter=10,

        textColor=colors.HexColor(
            "#1f4e78"
        )
    )


    normal_style = ParagraphStyle(

        "LoanNormal",

        parent=styles["BodyText"],

        fontSize=10,

        leading=15
    )


    story = []


    # ====================================
    # TITLE
    # ====================================

    story.append(

        Paragraph(

            "AI Loan Processing Report",

            title_style
        )
    )


    story.append(
        Spacer(
            1,
            0.2 * inch
        )
    )


    generated_time = datetime.now().strftime(
        "%d %B %Y, %I:%M %p"
    )


    summary_data = [

        [
            "Application ID",
            str(application_id)
        ],

        [
            "Generated",
            generated_time
        ]
    ]


    summary_table = Table(

        summary_data,

        colWidths=[
            2 * inch,
            4 * inch
        ]
    )


    summary_table.setStyle(

        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor(
                    "#1f4e78"
                )
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (0, -1),
                colors.white
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )


    story.append(
        summary_table
    )


    # ====================================
    # APPLICATION DETAILS
    # ====================================

    story.append(
        Paragraph(
            "Application Details",
            heading_style
        )
    )

    application_data = [
        ["Applicant Name", format_value(result.get("applicant_name"))],
        ["Date of Birth", format_value(result.get("date_of_birth"))],
        ["PAN", format_value(result.get("pan"))],
        ["Mobile", format_value(result.get("mobile"))],
        ["Email", format_value(result.get("email"))],
        ["Address", format_value(result.get("applicant_address"))],
        ["Employer", format_value(result.get("employer"))],
        ["Years of Experience", format_value(result.get("years_of_experience"))],
        ["Current Employment", format_value(result.get("current_employment_years"))],
        ["Gross Monthly Income", format_currency(result.get("gross_monthly_income", 0))],
        ["Net Monthly Income", format_currency(result.get("net_monthly_income", 0))],
        ["Existing Monthly EMI", format_currency(result.get("existing_monthly_emi", 0))],
        ["Requested Loan Amount", format_currency(result.get("requested_loan_amount", 0))],
        ["Loan Tenure", format_value(result.get("loan_tenure_years")) + " years"],
        ["Interest Rate", format_value(result.get("interest_rate")) + "%"],
        ["Loan Purpose", format_value(result.get("loan_purpose"))],
        ["Property Value", format_currency(result.get("property_value", 0))]
    ]

    application_table = Table(
        application_data,
        colWidths=[2.5 * inch, 3.5 * inch]
    )

    application_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e9f0f7")),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ])
    )

    story.append(application_table)


    # ====================================
    # FINAL DECISION
    # ====================================

    story.append(

        Paragraph(
            "Final Decision",
            heading_style
        )
    )


    final_decision = result.get(
        "final_decision",
        {}
    )


    decision_data = [

        [
            "Decision",
            format_value(
                final_decision.get(
                    "final_decision"
                )
            )
        ],

        [
            "Routing",
            format_value(
                final_decision.get(
                    "routing"
                )
            )
        ],

        [
            "Human Review Required",
            format_value(
                final_decision.get(
                    "human_review_required"
                )
            )
        ]
    ]


    decision_table = Table(

        decision_data,

        colWidths=[
            2.5 * inch,
            3.5 * inch
        ]
    )


    decision_table.setStyle(

        TableStyle([

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor(
                    "#e9f0f7"
                )
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )


    story.append(
        decision_table
    )


    # ====================================
    # EXECUTIVE SUMMARY
    # ====================================

    story.append(

        Paragraph(
            "Executive Summary",
            heading_style
        )
    )


    executive_summary = (
        build_decision_based_executive_summary(
            result
        )
    )


    story.append(

        Paragraph(

            html.escape(
                executive_summary
            ),

            normal_style
        )
    )


    # ====================================
    # DOCUMENT STATUS
    # ====================================

    story.append(

        Paragraph(
            "Document Status",
            heading_style
        )
    )


    document_checklist = result.get(
        "document_checklist",
        {}
    )


    document_data = [

        [
            "Uploaded",

            str(
                result.get(
                    "documents_uploaded",
                    0
                )
            )
        ],

        [
            "Required",

            str(
                len(
                    document_checklist.get(
                        "required_documents",
                        []
                    )
                )
            )
        ],

        [
            "Satisfied",

            str(
                len(
                    document_checklist.get(
                        "satisfied_documents",
                        []
                    )
                )
            )
        ],

        [
            "Missing",

            str(
                len(
                    document_checklist.get(
                        "missing_documents",
                        []
                    )
                )
            )
        ]
    ]


    document_table = Table(

        document_data,

        colWidths=[
            2.5 * inch,
            3.5 * inch
        ]
    )


    document_table.setStyle(

        TableStyle([

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor(
                    "#f2f2f2"
                )
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )


    story.append(
        document_table
    )


    # ====================================
    # MISSING DOCUMENTS
    # ====================================

    missing_documents = document_checklist.get(
        "missing_documents",
        []
    )


    if missing_documents:

        story.append(
            Spacer(
                1,
                0.15 * inch
            )
        )


        missing_text = (
            "<b>Missing Documents:</b><br/>"
            +
            "<br/>".join(
                [
                    f"• {html.escape(str(doc))}"
                    for doc in missing_documents
                ]
            )
        )


        story.append(

            Paragraph(
                missing_text,
                normal_style
            )
        )


    # ====================================
    # VERIFICATION
    # ====================================

    story.append(

        Paragraph(
            "Verification Results",
            heading_style
        )
    )


    verification = result.get(
        "verification",
        {}
    )


    verification_data = [

        [
            "Total Checks",
            verification.get(
                "total_checks",
                0
            )
        ],

        [
            "Matches",
            verification.get(
                "matches",
                0
            )
        ],

        [
            "Mismatches",
            verification.get(
                "mismatches",
                0
            )
        ],

        [
            "Insufficient Data",
            verification.get(
                "insufficient_data",
                0
            )
        ],

        [
            "Overall Status",
            format_value(
                verification.get(
                    "overall_status"
                )
            )
        ]
    ]


    verification_table = Table(

        verification_data,

        colWidths=[
            2.5 * inch,
            3.5 * inch
        ]
    )


    verification_table.setStyle(

        TableStyle([

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor(
                    "#e9f0f7"
                )
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )


    story.append(
        verification_table
    )


    # ====================================
    # UNDERWRITING
    # ====================================

    story.append(

        Paragraph(
            "Underwriting Results",
            heading_style
        )
    )


    underwriting = result.get(
        "underwriting",
        {}
    )


    underwriting_data = [

        [
            "Decision",
            format_value(
                underwriting.get(
                    "decision"
                )
            )
        ],

        [
            "Passed",
            underwriting.get(
                "passed",
                0
            )
        ],

        [
            "Failed",
            underwriting.get(
                "failed",
                0
            )
        ],

        [
            "Review Required",
            underwriting.get(
                "review_required",
                0
            )
        ]
    ]


    underwriting_table = Table(

        underwriting_data,

        colWidths=[
            2.5 * inch,
            3.5 * inch
        ]
    )


    underwriting_table.setStyle(

        TableStyle([

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor(
                    "#f2f2f2"
                )
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )


    story.append(
        underwriting_table
    )


    # ====================================
    # RISK
    # ====================================

    story.append(

        Paragraph(
            "Risk Assessment",
            heading_style
        )
    )


    risk = result.get(
        "risk",
        {}
    )


    risk_data = [

        [
            "Risk Score",
            f"{risk.get('risk_score', 0)} / 100"
        ],

        [
            "Risk Level",
            format_value(
                risk.get(
                    "risk_level"
                )
            )
        ],

        [
            "Human Review Required",
            format_value(
                risk.get(
                    "human_review_required"
                )
            )
        ],

        [
            "Recommendation",
            format_value(
                risk.get(
                    "recommendation"
                )
            )
        ]
    ]


    risk_table = Table(

        risk_data,

        colWidths=[
            2.5 * inch,
            3.5 * inch
        ]
    )


    risk_table.setStyle(

        TableStyle([

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor(
                    "#fff3cd"
                )
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )


    story.append(
        risk_table
    )


    # ====================================
    # KEY FINDINGS
    # ====================================

    story.append(

        Paragraph(
            "Key Findings",
            heading_style
        )
    )


    ai_summary = result.get(
        "ai_summary",
        {}
    )


    key_findings = ai_summary.get(
        "key_findings",
        []
    )


    if key_findings:

        for finding in key_findings:

            story.append(

                Paragraph(

                    f"• {html.escape(str(finding))}",

                    normal_style
                )
            )

            story.append(
                Spacer(
                    1,
                    0.05 * inch
                )
            )

    else:

        story.append(

            Paragraph(
                "No key findings available.",
                normal_style
            )
        )


    # ====================================
    # RECOMMENDED ACTIONS
    # ====================================

    story.append(

        Paragraph(
            "Recommended Actions",
            heading_style
        )
    )


    recommended_actions = ai_summary.get(
        "recommended_actions",
        []
    )


    if recommended_actions:

        for index, action in enumerate(
            recommended_actions,
            start=1
        ):

            story.append(

                Paragraph(

                    f"{index}. "
                    f"{html.escape(str(action))}",

                    normal_style
                )
            )

            story.append(
                Spacer(
                    1,
                    0.05 * inch
                )
            )

    else:

        story.append(

            Paragraph(
                "No recommended actions available.",
                normal_style
            )
        )


    # ====================================
    # BUILD PDF
    # ====================================

    doc.build(
        story
    )


    return pdf_path


# ========================================
# CREATE PDF PREVIEW
# ========================================

def create_pdf_preview(pdf_path):

    if not pdf_path:
        return ""

    if not os.path.exists(pdf_path):
        return ""

    with open(
        pdf_path,
        "rb"
    ) as pdf_file:

        encoded_pdf = base64.b64encode(
            pdf_file.read()
        ).decode(
            "utf-8"
        )


    # KEEPING THE EXISTING BASE64 IFRAME
    preview_html = f"""

    <iframe

        src="data:application/pdf;base64,{encoded_pdf}"

        width="100%"

        height="800px"

        style="
            border: 1px solid #ccc;
            border-radius: 10px;
            background: white;
        "

    >
    </iframe>

    """


    return preview_html


# ========================================
# PROCESSING STATUS
# ========================================

def create_processing_status(
    stage="Processing",
    message="Processing loan application..."
):

    return f"""
    <div style="
        padding: 14px 18px;
        margin: 10px 0;
        border-radius: 10px;
        background: #eef6ff;
        border: 1px solid #b9d7f5;
        color: #1f4e78;
        font-family: Arial, sans-serif;
    ">
        <div style="
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 4px;
        ">
            ⏳ {html.escape(str(stage))}
        </div>

        <div style="
            font-size: 13px;
            opacity: 0.9;
        ">
            {html.escape(str(message))}
        </div>
    </div>
    """


# ========================================
# PIPELINE STATUS
# ========================================

def create_pipeline_status(
    completed_stage=None,
    error=False
):

    stages = [
        ("1", "Application"),
        ("2", "Document Processing"),
        ("3", "Verification"),
        ("4", "Underwriting"),
        ("5", "Risk Assessment"),
        ("6", "Final Decision"),
        ("7", "Report Generation")
    ]

    completed_index = 0

    if completed_stage is not None:

        try:
            completed_index = int(
                completed_stage
            )
        except Exception:
            completed_index = 0


    items = []

    for index, (number, name) in enumerate(
        stages,
        start=1
    ):

        if error and index == completed_index + 1:

            icon = "❌"
            status = "Error"

        elif index <= completed_index:

            icon = "✅"
            status = "Completed"

        elif index == completed_index + 1:

            icon = "⏳"
            status = "Processing"

        else:

            icon = "○"
            status = "Pending"


        items.append(
            f"""
            <div style="
                display:flex;
                align-items:center;
                gap:10px;
                padding:7px 0;
                font-family:Arial,sans-serif;
                font-size:13px;
            ">
                <span style="
                    width:24px;
                    height:24px;
                    display:inline-flex;
                    align-items:center;
                    justify-content:center;
                    border-radius:50%;
                    background:#f3f3f3;
                    font-size:12px;
                ">
                    {icon}
                </span>

                <span>
                    <b>{number}. {html.escape(name)}</b>
                    <span style="
                        margin-left:6px;
                        color:#777;
                    ">
                        {status}
                    </span>
                </span>
            </div>
            """
        )


    return f"""
    <div style="
        padding:15px 18px;
        border:1px solid #ddd;
        border-radius:10px;
        background:#fff;
        margin:10px 0;
    ">

        <div style="
            font-size:15px;
            font-weight:700;
            margin-bottom:8px;
        ">
            🔄 Loan Processing Pipeline
        </div>

        {''.join(items)}

    </div>
    """


# ========================================
# MAIN FUNCTION FOR GRADIO
# ========================================

def run_loan_application_with_pdf(

    full_name,
    date_of_birth,
    pan,
    mobile,
    email,
    address,
    employer,
    years_of_experience,
    current_employment_years,
    gross_monthly_income,
    net_monthly_income,
    existing_monthly_emi,
    requested_loan_amount,
    loan_tenure_years,
    interest_rate,
    loan_purpose,
    property_value,
    uploaded_files
):

    try:

        # ====================================
        # INITIAL STATUS
        # ====================================

        processing_status = create_processing_status(
            "Application",
            "Starting loan application processing..."
        )

        pipeline_progress = create_pipeline_status(
            completed_stage=0
        )


        # ====================================
        # RUN EXISTING LOAN PIPELINE
        # ====================================

        result, loan_state = run_loan_application(

            full_name,

            date_of_birth,

            pan,

            mobile,

            email,

            address,

            employer,

            years_of_experience,

            current_employment_years,

            gross_monthly_income,

            net_monthly_income,

            existing_monthly_emi,

            requested_loan_amount,

            loan_tenure_years,

            interest_rate,

            loan_purpose,

            property_value,

            uploaded_files
        )


        # ====================================
        # NEVER CREATE A SUCCESS PDF FROM AN ERROR RESULT
        # ====================================

        if not isinstance(result, dict) or result.get("status") != "SUCCESS":
            error_message = (
                result.get("message", "Loan pipeline failed.")
                if isinstance(result, dict)
                else "Loan pipeline returned an invalid result."
            )
            return (
                result if isinstance(result, dict) else {
                    "status": "ERROR",
                    "message": error_message
                },
                loan_state,
                create_processing_status("Processing Error", error_message),
                create_pipeline_status(completed_stage=0, error=True),
                f"<div><h3>Processing Error</h3><p>{html.escape(str(error_message))}</p></div>",
                "",
                None
            )


        # ====================================
        # PIPELINE COMPLETED
        # ====================================

        processing_status = create_processing_status(
            "Report Generation",
            "Loan workflow completed. Generating final report and PDF..."
        )

        pipeline_progress = create_pipeline_status(
            completed_stage=6
        )


        # ====================================
        # CREATE HUMAN READABLE REPORT
        # ====================================

        report_preview = generate_html_report(
            result
        )


        # ====================================
        # GENERATE PDF
        # ====================================

        pdf_path = generate_loan_pdf(
            result
        )


        # ====================================
        # CREATE WEBSITE PDF PREVIEW
        # ====================================

        pdf_preview = create_pdf_preview(
            pdf_path
        )


        # ====================================
        # FINAL STATUS
        # ====================================

        processing_status = create_processing_status(
            "Completed",
            "Loan application processed successfully."
        )

        pipeline_progress = create_pipeline_status(
            completed_stage=7
        )


        # ====================================
        # RETURN TO GRADIO
        #
        # 7 OUTPUTS
        # ====================================

        return (

            result,

            loan_state,

            processing_status,

            pipeline_progress,

            report_preview,

            pdf_preview,

            pdf_path
        )


    except Exception as e:

        error_message = str(e)


        # ====================================
        # ERROR STATUS
        # ====================================

        processing_status = f"""
        <div style="
            padding:18px;
            margin:10px 0;
            border-radius:10px;
            background:#fff0f0;
            border:1px solid #f0b5b5;
            color:#a00000;
            font-family:Arial,sans-serif;
        ">

            <div style="
                font-size:16px;
                font-weight:700;
                margin-bottom:6px;
            ">
                ❌ Processing Error
            </div>

            <div style="
                font-size:13px;
            ">
                {html.escape(error_message)}
            </div>

        </div>
        """


        pipeline_progress = create_pipeline_status(
            completed_stage=0,
            error=True
        )


        error_result = {

            "status": "ERROR",

            "message": error_message
        }


        error_html = f"""
        <div style="
            padding:20px;
            color:#a00000;
            background:#fff0f0;
            border:1px solid #f0b5b5;
            border-radius:10px;
            font-family:Arial,sans-serif;
        ">

            <h3>
                Processing Error
            </h3>

            <p>
                {html.escape(error_message)}
            </p>

        </div>
        """


        return (

            error_result,

            {},

            processing_status,

            pipeline_progress,

            error_html,

            "",

            None
        )


# ========================================
# SUCCESS MESSAGE
# ========================================

print(
    "✅ Updated loan application + PDF processing functions loaded successfully"
)

print(
    "✅ Existing base64 PDF preview preserved"
)

print(
    "✅ Main Gradio function now returns 7 outputs"
)

print(
    "✅ Processing status + pipeline status added"
)

# ===== FASTAPI WEBSITE CELL 37 =====
# ============================================================
# GEN AI MORTGAGE LOAN APPLICATION
# COMPLETE FASTAPI WEBSITE
# PREMIUM UI + CINEMATIC ANIMATIONS + 11 AGENT TRACKER
# ============================================================
#
# IMPORTANT:
# Run your BACKEND / AGENT cells first.
# This cell replaces the old Gradio UI.
#
# ============================================================



# ============================================================
# IMPORTS
# ============================================================

import os
import json
import uuid
import time
import shutil
import threading
import inspect
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from typing import List, Optional

import uvicorn


# ============================================================
# BACKEND CHECK
# ============================================================

if "run_loan_application_with_pdf" not in globals():
    raise RuntimeError(
        "run_loan_application_with_pdf was not found. "
        "Please run your backend / agent cells before running this UI cell."
    )

print("Backend function detected:")
print(run_loan_application_with_pdf)


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = Path(os.getenv("APP_DATA_DIR", str(Path.cwd() / "gen_ai_mortgage_website")))
UPLOAD_DIR = BASE_DIR / "uploads"
JOB_DIR = BASE_DIR / "jobs"

BASE_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
JOB_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FASTAPI
# ============================================================

loan_web_app = FastAPI(
    title="Gen AI Mortgage Loan Application",
    version="2.0"
)


# ============================================================
# GLOBAL JOB STORAGE
# ============================================================

JOBS = {}
JOBS_LOCK = threading.Lock()


# ============================================================
# 11 AI AGENTS
# ============================================================

AGENTS = [
    {
        "id": 1,
        "short": "INTAKE",
        "name": "Document Intake",
        "description": "Classifying submitted documents"
    },
    {
        "id": 2,
        "short": "CHECK",
        "name": "Document Checklist",
        "description": "Checking required documents"
    },
    {
        "id": 3,
        "short": "EXTRACT",
        "name": "Data Extraction",
        "description": "Extracting applicant information"
    },
    {
        "id": 4,
        "short": "VERIFY",
        "name": "Document Verification",
        "description": "Cross-document verification"
    },
    {
        "id": 5,
        "short": "UNDERWRITE",
        "name": "Loan Underwriting",
        "description": "Evaluating loan eligibility"
    },
    {
        "id": 6,
        "short": "RISK",
        "name": "Risk & Fraud",
        "description": "Detecting risk and exceptions"
    },
    {
        "id": 7,
        "short": "SUMMARY",
        "name": "AI Case Summary",
        "description": "Generating case recommendation"
    },
    {
        "id": 8,
        "short": "DECISION",
        "name": "Final Decision",
        "description": "Determining loan routing"
    },
    {
        "id": 9,
        "short": "REVIEW",
        "name": "Human Review",
        "description": "Preparing review case"
    },
    {
        "id": 10,
        "short": "RESOLVE",
        "name": "Reviewer Resolution",
        "description": "Resolving review outcome"
    },
    {
        "id": 11,
        "short": "FINAL",
        "name": "Final Resolution",
        "description": "Completing final resolution"
    }
]


# ============================================================
# SAFE SERIALIZATION
# ============================================================

def safe_json(value):
    try:
        return json.loads(
            json.dumps(
                value,
                default=str,
                ensure_ascii=False
            )
        )
    except Exception:
        return str(value)


# ============================================================
# NUMERIC CONVERSION
# ============================================================

def to_float(value, field_name):
    """
    Safely convert numeric form fields.

    IMPORTANT:
    Loan Purpose is NEVER passed through this function.
    """

    if value is None:
        return 0.0

    text = str(value).strip()

    if text == "":
        return 0.0

    try:
        return float(text.replace(",", "").replace("₹", "").strip())
    except Exception:
        raise ValueError(
            f"{field_name} must be a number. Received: {value}"
        )


def to_int(value, field_name):
    if value is None:
        return 0

    text = str(value).strip()

    if text == "":
        return 0

    try:
        return int(float(text))
    except Exception:
        raise ValueError(
            f"{field_name} must be a whole number. Received: {value}"
        )


# ============================================================
# CREATE JOB
# ============================================================

def create_job():
    job_id = uuid.uuid4().hex

    job = {
        "id": job_id,
        "status": "queued",
        "message": "Application ready",
        "progress": 0,
        "active_agent": 0,
        "completed_agents": 0,
        "agents": [
            {
                "id": agent["id"],
                "short": agent["short"],
                "name": agent["name"],
                "description": agent["description"],
                "status": "waiting"
            }
            for agent in AGENTS
        ],
        "result": None,
        "loan_state": None,
        "processing_status": None,
        "pipeline_progress": None,
        "report_preview": None,
        "pdf_path": None,
        "input_snapshot": None,
        "error": None,
        "created_at": time.time()
    }

    with JOBS_LOCK:
        JOBS[job_id] = job

    return job_id


# ============================================================
# UPDATE AGENT
# ============================================================

def update_agent(job_id, agent_number, status, message=None):
    with JOBS_LOCK:

        job = JOBS.get(job_id)

        if job is None:
            return

        if agent_number < 1 or agent_number > 11:
            return

        agent = job["agents"][agent_number - 1]
        agent["status"] = status

        if status == "running":
            job["active_agent"] = agent_number
            job["status"] = "processing"

            if message:
                job["message"] = message
            else:
                job["message"] = agent["name"]

        elif status == "completed":

            completed = 0

            for item in job["agents"]:
                if item["status"] == "completed":
                    completed += 1

            job["completed_agents"] = completed
            job["progress"] = int((completed / 11) * 100)

            job["message"] = (
                f"{agent['name']} completed"
            )

        elif status == "error":

            job["status"] = "error"
            job["error"] = message or "Agent processing error"
            job["message"] = message or "Processing error"


# ============================================================
# PROCESS JOB
# ============================================================

def process_loan_job(job_id, application_args):

    try:

        with JOBS_LOCK:
            JOBS[job_id]["status"] = "processing"
            JOBS[job_id]["message"] = "AI loan processing started"

        # ----------------------------------------------------
        # CALLBACK
        # ----------------------------------------------------

        def progress_callback(agent_number, status, loan_state=None):

            try:

                agent_number = int(agent_number)

                if status == "completed":

                    update_agent(
                        job_id,
                        agent_number,
                        "completed"
                    )

                    next_agent = agent_number + 1

                    if next_agent <= 11:

                        update_agent(
                            job_id,
                            next_agent,
                            "running"
                        )

                elif status == "running":

                    update_agent(
                        job_id,
                        agent_number,
                        "running"
                    )

            except Exception as callback_error:

                print(
                    "Progress callback error:",
                    callback_error
                )

        # ----------------------------------------------------
        # FIRST AGENT
        # ----------------------------------------------------

        update_agent(
            job_id,
            1,
            "running"
        )

        # ----------------------------------------------------
        # CHECK BACKEND SIGNATURE
        # ----------------------------------------------------

        try:
            backend_signature = inspect.signature(
                run_loan_application_with_pdf
            )

            supports_callback = (
                "progress_callback"
                in backend_signature.parameters
            )

        except Exception:

            supports_callback = False

        # ----------------------------------------------------
        # RUN BACKEND
        # ----------------------------------------------------

        if supports_callback:

            output = run_loan_application_with_pdf(
                *application_args,
                progress_callback=progress_callback
            )

        else:

            output = run_loan_application_with_pdf(
                *application_args
            )

        # ----------------------------------------------------
        # EXPECTED BACKEND OUTPUT
        # ----------------------------------------------------
        #
        # result
        # loan_state
        # processing_status
        # pipeline_progress
        # report_preview
        # pdf_preview
        # pdf_path
        #
        # ----------------------------------------------------

        if isinstance(output, tuple) and len(output) >= 7:

            result = output[0]
            loan_state = output[1]
            processing_status = output[2]
            pipeline_progress = output[3]
            report_preview = output[4]
            pdf_preview = output[5]
            pdf_path = output[6]

        else:

            result = output
            loan_state = {}
            processing_status = None
            pipeline_progress = None
            report_preview = None
            pdf_preview = None
            pdf_path = None

        # ----------------------------------------------------
        # IF CALLBACK WAS NOT AVAILABLE
        # ----------------------------------------------------

        if not supports_callback:

            for number in range(1, 12):

                update_agent(
                    job_id,
                    number,
                    "completed"
                )

        else:

            # Make sure final state is complete
            for number in range(1, 12):

                with JOBS_LOCK:
                    state = JOBS[job_id]["agents"][number - 1]["status"]

                if state != "completed":

                    update_agent(
                        job_id,
                        number,
                        "completed"
                    )

        # ----------------------------------------------------
        # SAVE FINAL JOB
        # ----------------------------------------------------

        with JOBS_LOCK:

            job = JOBS[job_id]

            job["status"] = "completed"
            job["message"] = "Loan processing completed successfully"
            job["progress"] = 100
            job["active_agent"] = 0
            job["completed_agents"] = 11

            job["result"] = safe_json(result)
            job["loan_state"] = safe_json(loan_state)
            job["processing_status"] = safe_json(
                processing_status
            )
            job["pipeline_progress"] = safe_json(
                pipeline_progress
            )
            job["report_preview"] = safe_json(
                report_preview
            )
            job["pdf_path"] = (
                str(pdf_path)
                if pdf_path
                else None
            )

            for agent in job["agents"]:
                agent["status"] = "completed"

    except Exception as exc:

        error_text = str(exc)

        print(
            "LOAN PROCESSING ERROR:",
            repr(exc)
        )

        with JOBS_LOCK:

            job = JOBS.get(job_id)

            if job:

                job["status"] = "error"
                job["message"] = "Loan processing failed"
                job["error"] = error_text

                active_agent = job.get(
                    "active_agent",
                    1
                )

                try:
                    active_agent = int(active_agent)
                except Exception:
                    active_agent = 1

                if 1 <= active_agent <= 11:

                    job["agents"][
                        active_agent - 1
                    ]["status"] = "error"


# ============================================================
# HTML PAGE
# ============================================================

PAGE = r"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
    Gen AI Mortgage Loan Application
</title>

<style>

/* ============================================================
   ROOT
   ============================================================ */

:root {

    --bg: #06111f;
    --bg2: #091a2d;

    --surface: rgba(13, 30, 49, .76);
    --surface2: rgba(17, 39, 62, .72);

    --border: rgba(148, 191, 224, .15);
    --border2: rgba(92, 184, 255, .24);

    --text: #f5f9ff;
    --text2: #d9e7f4;
    --muted: #8ea6bb;
    --muted2: #678197;

    --blue: #59b9ff;
    --blue2: #3189ff;
    --cyan: #55e0d0;

    --green: #50e39b;
    --red: #ff6e7d;
    --amber: #f6c56c;

    --shadow:
        0 25px 80px rgba(0,0,0,.32);

    --radius: 24px;
}


/* ============================================================
   RESET
   ============================================================ */

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {

    margin: 0;

    min-height: 100vh;

    background:
        radial-gradient(
            circle at 12% 8%,
            rgba(49,137,255,.18),
            transparent 28%
        ),
        radial-gradient(
            circle at 86% 20%,
            rgba(85,224,208,.10),
            transparent 25%
        ),
        linear-gradient(
            145deg,
            #040c17 0%,
            #071525 50%,
            #06111f 100%
        );

    color: var(--text);

    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

    overflow-x: hidden;
}


/* ============================================================
   BACKGROUND GRAPHICS
   ============================================================ */

.background {

    position: fixed;

    inset: 0;

    z-index: -10;

    overflow: hidden;

    pointer-events: none;
}

.grid {

    position: absolute;

    inset: -20%;

    background-image:
        linear-gradient(
            rgba(105,165,211,.045) 1px,
            transparent 1px
        ),
        linear-gradient(
            90deg,
            rgba(105,165,211,.045) 1px,
            transparent 1px
        );

    background-size: 54px 54px;

    transform:
        perspective(700px)
        rotateX(58deg)
        translateY(18%);

    transform-origin: center bottom;

    mask-image:
        linear-gradient(
            to top,
            black,
            transparent 72%
        );

    animation:
        gridMove 18s linear infinite;
}

@keyframes gridMove {

    from {
        transform:
            perspective(700px)
            rotateX(58deg)
            translateY(18%);
    }

    to {
        transform:
            perspective(700px)
            rotateX(58deg)
            translateY(8%);
    }
}

.orb {

    position: absolute;

    border-radius: 50%;

    filter: blur(4px);

    opacity: .55;

    animation:
        floatOrb 9s ease-in-out infinite;
}

.orb.one {

    width: 360px;
    height: 360px;

    left: -130px;
    top: 80px;

    background:
        radial-gradient(
            circle,
            rgba(49,137,255,.20),
            transparent 70%
        );
}

.orb.two {

    width: 300px;
    height: 300px;

    right: -90px;
    top: 380px;

    background:
        radial-gradient(
            circle,
            rgba(85,224,208,.15),
            transparent 70%
        );

    animation-delay: -3s;
}

.orb.three {

    width: 240px;
    height: 240px;

    left: 45%;
    top: 65%;

    background:
        radial-gradient(
            circle,
            rgba(92,142,255,.12),
            transparent 70%
        );

    animation-delay: -6s;
}

@keyframes floatOrb {

    0%,
    100% {
        transform: translate3d(0,0,0);
    }

    50% {
        transform: translate3d(0,-35px,0);
    }
}


/* ============================================================
   START SCREEN
   ============================================================ */

.start-screen {

    position: fixed;

    inset: 0;

    z-index: 9999;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        radial-gradient(
            circle at 50% 42%,
            rgba(49,137,255,.14),
            transparent 30%
        ),
        #040b14;

    transition:
        opacity .8s ease,
        visibility .8s ease;
}

.start-screen.hide {

    opacity: 0;

    visibility: hidden;

    pointer-events: none;
}

.start-content {

    width: min(760px, 92vw);

    text-align: center;

    position: relative;

    padding: 30px;
}

.start-orbit {

    width: 190px;
    height: 190px;

    margin: 0 auto 34px;

    position: relative;

    display: flex;

    align-items: center;

    justify-content: center;
}

.start-orbit::before,
.start-orbit::after {

    content: "";

    position: absolute;

    inset: 0;

    border-radius: 50%;

    border: 1px solid
        rgba(89,185,255,.30);

    animation:
        orbitSpin 9s linear infinite;
}

.start-orbit::after {

    inset: 22px;

    border-color:
        rgba(85,224,208,.24);

    animation-direction: reverse;

    animation-duration: 6s;
}

@keyframes orbitSpin {

    to {
        transform: rotate(360deg);
    }
}

.start-core {

    width: 104px;
    height: 104px;

    border-radius: 30px;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        linear-gradient(
            145deg,
            #173d63,
            #0c2239
        );

    border:
        1px solid
        rgba(120,200,255,.30);

    box-shadow:
        0 0 60px
        rgba(49,137,255,.20),
        inset 0 1px 0
        rgba(255,255,255,.08);
}

.start-core span {

    font-size: 30px;

    font-weight: 900;

    letter-spacing: -2px;

    background:
        linear-gradient(
            135deg,
            #ffffff,
            #6bc9ff
        );

    -webkit-background-clip: text;

    color: transparent;
}

.start-kicker {

    display: inline-flex;

    align-items: center;

    gap: 8px;

    padding: 8px 13px;

    border:
        1px solid
        rgba(89,185,255,.18);

    background:
        rgba(13,34,55,.66);

    border-radius: 999px;

    color: #9fd8ff;

    font-size: 10px;

    font-weight: 800;

    letter-spacing: 1.5px;
}

.start-kicker i {

    width: 7px;
    height: 7px;

    border-radius: 50%;

    background: var(--green);

    box-shadow:
        0 0 0 5px
        rgba(80,227,155,.08);

    animation:
        pulse 1.5s infinite;
}

@keyframes pulse {

    50% {
        opacity: .4;
        transform: scale(.7);
    }
}

.start-title {

    margin: 24px 0 14px;

    font-size:
        clamp(42px, 7vw, 78px);

    line-height: .98;

    letter-spacing: -4px;

    font-weight: 900;
}

.start-title span {

    display: block;

    background:
        linear-gradient(
            100deg,
            #ffffff 5%,
            #7bcaff 42%,
            #64e1d1 88%
        );

    -webkit-background-clip: text;

    background-clip: text;

    color: transparent;
}

.start-subtitle {

    max-width: 610px;

    margin: auto;

    color: var(--muted);

    line-height: 1.75;

    font-size: 14px;
}

.enter-btn {

    margin-top: 32px;

    border: 0;

    color: white;

    padding: 15px 26px;

    border-radius: 15px;

    cursor: pointer;

    font-weight: 850;

    font-size: 13px;

    background:
        linear-gradient(
            100deg,
            #2d87ff,
            #4cb8ff,
            #48d7c5
        );

    box-shadow:
        0 14px 35px
        rgba(49,137,255,.24);

    transition:
        transform .25s ease,
        box-shadow .25s ease;
}

.enter-btn:hover {

    transform:
        translateY(-3px)
        scale(1.015);

    box-shadow:
        0 20px 50px
        rgba(49,137,255,.35);
}


/* ============================================================
   APP SHELL
   ============================================================ */

.app {

    width: min(1280px, calc(100% - 36px));

    margin: 0 auto;

    padding-bottom: 80px;
}


/* ============================================================
   TOPBAR
   ============================================================ */

.topbar {

    min-height: 78px;

    display: flex;

    align-items: center;

    justify-content: space-between;

    border-bottom:
        1px solid
        rgba(148,191,224,.10);
}

.brand {

    display: flex;

    align-items: center;

    gap: 12px;
}

.brand-logo {

    width: 43px;
    height: 43px;

    border-radius: 14px;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        linear-gradient(
            145deg,
            #1d5d94,
            #0c2944
        );

    border:
        1px solid
        rgba(119,201,255,.25);

    box-shadow:
        0 10px 30px
        rgba(0,0,0,.25);
}

.brand-logo span {

    font-size: 12px;

    font-weight: 900;

    color: white;
}

.brand-name {

    font-size: 18px;

    font-weight: 900;

    letter-spacing: -.7px;
}

.brand-name span {

    color: #62d8d0;
}

.brand-sub {

    color: var(--muted2);

    font-size: 9px;

    margin-top: 2px;

    letter-spacing: .7px;
}

.online {

    display: flex;

    align-items: center;

    gap: 8px;

    padding: 9px 13px;

    border:
        1px solid
        rgba(80,227,155,.16);

    background:
        rgba(26,67,57,.28);

    color: #91e9bd;

    border-radius: 999px;

    font-size: 9px;

    font-weight: 800;

    letter-spacing: .8px;
}

.online-dot {

    width: 7px;
    height: 7px;

    border-radius: 50%;

    background: var(--green);

    box-shadow:
        0 0 0 5px
        rgba(80,227,155,.07);

    animation: pulse 1.5s infinite;
}


/* ============================================================
   HERO
   ============================================================ */

.hero {

    display: grid;

    grid-template-columns:
        minmax(0, 1.15fr)
        minmax(320px, .85fr);

    gap: 40px;

    align-items: center;

    padding: 75px 0 65px;
}

.hero-kicker {

    display: inline-flex;

    align-items: center;

    gap: 8px;

    padding: 8px 12px;

    border-radius: 999px;

    background:
        rgba(20,53,82,.65);

    border:
        1px solid
        rgba(89,185,255,.17);

    color: #9bd7ff;

    font-size: 9px;

    font-weight: 850;

    letter-spacing: 1.3px;
}

.hero-kicker::before {

    content: "";

    width: 6px;
    height: 6px;

    border-radius: 50%;

    background: var(--cyan);

    box-shadow:
        0 0 12px
        rgba(85,224,208,.8);
}

.hero h1 {

    margin: 21px 0 18px;

    font-size:
        clamp(42px, 6vw, 76px);

    line-height: 1;

    letter-spacing: -4px;

    font-weight: 900;
}

.hero h1 span {

    background:
        linear-gradient(
            95deg,
            #ffffff,
            #75c9ff,
            #69ded0
        );

    -webkit-background-clip: text;

    color: transparent;
}

.hero p {

    max-width: 650px;

    color: var(--muted);

    font-size: 14px;

    line-height: 1.8;
}

.hero-stats {

    display: flex;

    gap: 10px;

    margin-top: 28px;

    flex-wrap: wrap;
}

.hero-stat {

    min-width: 130px;

    padding: 13px 15px;

    border:
        1px solid
        var(--border);

    background:
        rgba(11,30,49,.55);

    border-radius: 16px;

    backdrop-filter: blur(15px);
}

.hero-stat strong {

    display: block;

    font-size: 17px;
}

.hero-stat span {

    display: block;

    color: var(--muted2);

    font-size: 8px;

    font-weight: 800;

    letter-spacing: .9px;

    margin-top: 4px;
}


/* ============================================================
   HERO GRAPHIC
   ============================================================ */

.hero-visual {

    min-height: 390px;

    position: relative;

    display: flex;

    align-items: center;

    justify-content: center;
}

.halo {

    position: absolute;

    width: 330px;
    height: 330px;

    border-radius: 50%;

    border:
        1px solid
        rgba(89,185,255,.16);

    box-shadow:
        0 0 90px
        rgba(49,137,255,.10);

    animation:
        haloRotate 16s linear infinite;
}

.halo::before {

    content: "";

    position: absolute;

    inset: 28px;

    border-radius: 50%;

    border:
        1px dashed
        rgba(85,224,208,.17);
}

@keyframes haloRotate {

    to {
        transform: rotate(360deg);
    }
}

.house {

    width: 205px;

    height: 245px;

    position: relative;

    padding: 30px;

    border-radius: 28px;

    background:
        linear-gradient(
            145deg,
            rgba(22,57,88,.96),
            rgba(7,24,41,.96)
        );

    border:
        1px solid
        rgba(111,194,255,.25);

    box-shadow:
        0 35px 80px
        rgba(0,0,0,.35),
        inset 0 1px 0
        rgba(255,255,255,.08);

    transform:
        rotate(-3deg);

    animation:
        houseFloat 5s ease-in-out infinite;
}

@keyframes houseFloat {

    0%,
    100% {
        transform:
            rotate(-3deg)
            translateY(0);
    }

    50% {
        transform:
            rotate(-1deg)
            translateY(-12px);
    }
}

.roof {

    position: absolute;

    width: 110px;
    height: 110px;

    left: 48px;
    top: 34px;

    border-left:
        4px solid
        #6fcaff;

    border-top:
        4px solid
        #6fcaff;

    transform:
        rotate(45deg);

    filter:
        drop-shadow(
            0 0 12px
            rgba(89,185,255,.25)
        );
}

.house-body {

    position: absolute;

    left: 44px;
    right: 44px;

    top: 103px;
    bottom: 32px;

    border-radius: 10px 10px 5px 5px;

    background:
        linear-gradient(
            145deg,
            #123b5c,
            #0b263f
        );

    border:
        1px solid
        rgba(110,198,255,.18);
}

.window {

    position: absolute;

    width: 28px;
    height: 38px;

    left: 24px;
    top: 21px;

    border-radius: 5px;

    background:
        linear-gradient(
            145deg,
            #5edbff,
            #2e7fff
        );

    box-shadow:
        0 0 18px
        rgba(79,182,255,.35);
}

.door {

    position: absolute;

    width: 29px;
    height: 52px;

    right: 23px;
    bottom: 0;

    border-radius:
        6px 6px 0 0;

    background:
        #081827;

    border:
        1px solid
        rgba(255,255,255,.08);
}


/* ============================================================
   SECTION
   ============================================================ */

.section {

    margin-top: 22px;
}

.section-head {

    display: flex;

    align-items: center;

    gap: 14px;

    margin-bottom: 16px;
}

.section-number {

    width: 38px;
    height: 38px;

    border-radius: 12px;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        linear-gradient(
            145deg,
            #173d60,
            #0b2239
        );

    border:
        1px solid
        rgba(89,185,255,.17);

    color: #a9ddff;

    font-size: 10px;

    font-weight: 900;
}

.section-kicker {

    color: #6ecbff;

    font-size: 8px;

    font-weight: 900;

    letter-spacing: 1.5px;
}

.section-title {

    font-size: 21px;

    font-weight: 850;

    letter-spacing: -.7px;

    margin-top: 2px;
}

.section-description {

    color: var(--muted2);

    font-size: 10px;

    margin-top: 3px;
}


/* ============================================================
   CARD
   ============================================================ */

.card {

    position: relative;

    padding: 26px;

    border-radius: var(--radius);

    background:
        linear-gradient(
            145deg,
            rgba(16,37,59,.82),
            rgba(8,24,40,.72)
        );

    border:
        1px solid
        var(--border);

    box-shadow:
        var(--shadow);

    backdrop-filter:
        blur(20px);

    overflow: hidden;
}

.card::before {

    content: "";

    position: absolute;

    left: 0;
    right: 0;
    top: 0;

    height: 1px;

    background:
        linear-gradient(
            90deg,
            transparent,
            rgba(105,201,255,.35),
            transparent
        );
}


/* ============================================================
   FORM GRID
   ============================================================ */

.form-grid {

    display: grid;

    grid-template-columns:
        repeat(2, minmax(0,1fr));

    gap: 17px;
}

.field {

    display: flex;

    flex-direction: column;

    gap: 7px;
}

.field.full {

    grid-column:
        1 / -1;
}

label {

    color: #cfe0ee;

    font-size: 10px;

    font-weight: 750;
}

input,
select,
textarea {

    width: 100%;

    min-height: 47px;

    border-radius: 13px;

    border:
        1px solid
        rgba(148,191,224,.14);

    outline: none;

    background:
        rgba(4,17,30,.72);

    color: #f5f9ff;

    padding: 0 14px;

    font-size: 12px;

    transition:
        border .2s ease,
        box-shadow .2s ease,
        transform .2s ease,
        background .2s ease;
}

textarea {

    padding-top: 13px;

    min-height: 96px;

    resize: vertical;
}

input::placeholder,
textarea::placeholder {

    color: #567087;
}

input:hover,
select:hover,
textarea:hover {

    border-color:
        rgba(89,185,255,.30);

    background:
        rgba(7,23,39,.86);
}

input:focus,
select:focus,
textarea:focus {

    border-color:
        rgba(89,185,255,.65);

    box-shadow:
        0 0 0 4px
        rgba(49,137,255,.08),
        0 8px 30px
        rgba(0,0,0,.15);

    transform:
        translateY(-1px);
}

select option {

    background: #0b1d30;

    color: white;
}


/* ============================================================
   DOCUMENT UPLOAD
   ============================================================ */

.upload-box {

    border:
        1px dashed
        rgba(89,185,255,.28);

    border-radius: 18px;

    min-height: 190px;

    display: flex;

    flex-direction: column;

    align-items: center;

    justify-content: center;

    text-align: center;

    background:
        radial-gradient(
            circle at center,
            rgba(49,137,255,.08),
            transparent 65%
        );

    transition:
        border .25s ease,
        background .25s ease,
        transform .25s ease;

    cursor: pointer;
}

.upload-box:hover {

    border-color:
        rgba(89,185,255,.60);

    background:
        radial-gradient(
            circle at center,
            rgba(49,137,255,.14),
            transparent 65%
        );

    transform:
        translateY(-2px);
}

.upload-icon {

    width: 55px;
    height: 55px;

    border-radius: 17px;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        linear-gradient(
            145deg,
            #163e61,
            #0c253d
        );

    color: #8dd5ff;

    font-size: 23px;

    border:
        1px solid
        rgba(89,185,255,.20);

    margin-bottom: 12px;
}

.upload-title {

    color: #eaf5ff;

    font-size: 12px;

    font-weight: 800;
}

.upload-sub {

    color: var(--muted2);

    font-size: 9px;

    margin-top: 6px;
}

.upload-badge {

    margin-top: 11px;

    padding: 5px 8px;

    border-radius: 7px;

    background:
        rgba(85,224,208,.08);

    color: #83ddd3;

    border:
        1px solid
        rgba(85,224,208,.13);

    font-size: 7px;

    font-weight: 900;

    letter-spacing: 1px;
}

.file-list {

    width: 100%;

    margin-top: 13px;

    display: none;
}

.file-item {

    display: flex;

    align-items: center;

    justify-content: space-between;

    padding: 9px 11px;

    margin-top: 7px;

    border-radius: 10px;

    background:
        rgba(6,20,34,.75);

    border:
        1px solid
        rgba(148,191,224,.10);

    font-size: 9px;

    color: #b8ccdc;
}


/* ============================================================
   ACTION CARD
   ============================================================ */

.action-card {

    margin-top: 24px;

    padding: 22px;

    border-radius: 21px;

    background:
        linear-gradient(
            115deg,
            rgba(19,59,92,.90),
            rgba(8,35,57,.88)
        );

    border:
        1px solid
        rgba(89,185,255,.19);

    position: relative;

    overflow: hidden;
}

.action-card::after {

    content: "";

    position: absolute;

    width: 300px;
    height: 300px;

    right: -150px;
    top: -200px;

    border-radius: 50%;

    background:
        radial-gradient(
            circle,
            rgba(85,224,208,.16),
            transparent 65%
        );

    pointer-events: none;
}

.action-top {

    display: flex;

    align-items: center;

    gap: 12px;

    margin-bottom: 15px;
}

.action-icon {

    width: 39px;
    height: 39px;

    border-radius: 12px;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        rgba(85,224,208,.10);

    border:
        1px solid
        rgba(85,224,208,.18);

    color: #75e2d8;
}

.action-title {

    font-size: 13px;

    font-weight: 850;
}

.action-sub {

    color: var(--muted);

    font-size: 9px;

    margin-top: 3px;
}

.process-btn {

    width: 100%;

    min-height: 58px;

    border: 0;

    border-radius: 15px;

    cursor: pointer;

    color: white;

    font-size: 13px;

    font-weight: 900;

    letter-spacing: .1px;

    background:
        linear-gradient(
            100deg,
            #277eff,
            #43a9ff,
            #40d5c2
        );

    box-shadow:
        0 15px 38px
        rgba(49,137,255,.22);

    transition:
        transform .22s ease,
        box-shadow .22s ease,
        filter .22s ease;
}

.process-btn:hover {

    transform:
        translateY(-3px);

    box-shadow:
        0 22px 50px
        rgba(49,137,255,.34);

    filter: brightness(1.05);
}

.process-btn:disabled {

    opacity: .55;

    cursor: wait;

    transform: none;
}

.new-btn {

    margin-top: 10px;

    width: 100%;

    min-height: 44px;

    border-radius: 13px;

    cursor: pointer;

    background:
        rgba(5,19,32,.58);

    border:
        1px solid
        rgba(148,191,224,.15);

    color: #b9ccdc;

    font-size: 10px;

    font-weight: 800;

    transition: .2s ease;
}

.new-btn:hover {

    color: white;

    border-color:
        rgba(89,185,255,.34);

    background:
        rgba(13,37,58,.8);
}

.secure {

    text-align: center;

    margin-top: 10px;

    color: #607a8f;

    font-size: 8px;
}


/* ============================================================
   TRACKER
   ============================================================ */

.tracker-card {

    margin-top: 20px;

    padding: 26px;

    border-radius: 24px;

    background:
        linear-gradient(
            145deg,
            rgba(12,31,50,.92),
            rgba(6,19,33,.90)
        );

    border:
        1px solid
        rgba(89,185,255,.13);

    box-shadow:
        var(--shadow);
}

.tracker-head {

    display: flex;

    align-items: flex-start;

    justify-content: space-between;

    gap: 20px;

    margin-bottom: 22px;
}

.tracker-kicker {

    color: #67cbff;

    font-size: 8px;

    font-weight: 900;

    letter-spacing: 1.5px;
}

.tracker-title {

    margin-top: 4px;

    font-size: 21px;

    font-weight: 900;

    letter-spacing: -.7px;
}

.tracker-desc {

    margin-top: 4px;

    color: var(--muted2);

    font-size: 9px;
}

.tracker-status {

    padding: 8px 12px;

    border-radius: 999px;

    background:
        rgba(49,137,255,.08);

    border:
        1px solid
        rgba(89,185,255,.14);

    color: #91d4ff;

    font-size: 8px;

    font-weight: 900;

    white-space: nowrap;
}

.progress-wrap {

    padding: 16px;

    border-radius: 16px;

    background:
        rgba(3,15,27,.65);

    border:
        1px solid
        rgba(148,191,224,.08);

    margin-bottom: 18px;
}

.progress-line {

    display: flex;

    justify-content: space-between;

    color: var(--muted);

    font-size: 9px;
}

.progress-line strong {

    color: #d9ecfa;
}

.progress-bar {

    height: 7px;

    border-radius: 99px;

    background:
        rgba(148,191,224,.10);

    overflow: hidden;

    margin-top: 10px;
}

.progress-fill {

    width: 0%;

    height: 100%;

    border-radius: inherit;

    background:
        linear-gradient(
            90deg,
            #348cff,
            #5dc9ff,
            #55dfd0
        );

    box-shadow:
        0 0 20px
        rgba(89,185,255,.35);

    transition:
        width .45s ease;
}

.current-agent {

    display: flex;

    align-items: center;

    gap: 12px;

    padding: 13px;

    border-radius: 15px;

    background:
        linear-gradient(
            120deg,
            rgba(29,81,124,.30),
            rgba(22,72,71,.18)
        );

    border:
        1px solid
        rgba(89,185,255,.12);

    margin-bottom: 20px;
}

.current-icon {

    width: 37px;
    height: 37px;

    border-radius: 12px;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        linear-gradient(
            145deg,
            #2f8eff,
            #3bcfbe
        );

    color: white;

    font-size: 14px;

    animation:
        currentPulse 1.5s infinite;
}

@keyframes currentPulse {

    50% {
        box-shadow:
            0 0 0 7px
            rgba(89,185,255,.07);
    }
}

.current-info {

    flex: 1;
}

.current-label {

    color: #70bfe9;

    font-size: 7px;

    font-weight: 900;

    letter-spacing: 1px;
}

.current-name {

    margin-top: 3px;

    font-size: 11px;

    font-weight: 850;
}

.current-count {

    font-size: 10px;

    color: #79cfff;

    font-weight: 900;
}


/* ============================================================
   AGENT GRID
   ============================================================ */

.agent-grid {

    display: grid;

    grid-template-columns:
        repeat(3, minmax(0,1fr));

    gap: 10px;
}

.agent {

    min-height: 93px;

    padding: 13px;

    border-radius: 15px;

    background:
        rgba(4,17,30,.56);

    border:
        1px solid
        rgba(148,191,224,.08);

    position: relative;

    overflow: hidden;

    transition:
        transform .25s ease,
        border .25s ease,
        background .25s ease;
}

.agent:hover {

    transform:
        translateY(-3px);

    border-color:
        rgba(89,185,255,.20);

    background:
        rgba(8,27,45,.75);
}

.agent.running {

    border-color:
        rgba(89,185,255,.38);

    background:
        linear-gradient(
            145deg,
            rgba(22,62,95,.65),
            rgba(5,24,39,.68)
        );

    box-shadow:
        inset 0 0 30px
        rgba(49,137,255,.06);
}

.agent.completed {

    border-color:
        rgba(80,227,155,.16);

    background:
        rgba(8,37,33,.42);
}

.agent.error {

    border-color:
        rgba(255,110,125,.28);

    background:
        rgba(59,18,27,.45);
}

.agent-top {

    display: flex;

    align-items: center;

    justify-content: space-between;
}

.agent-number {

    width: 25px;
    height: 25px;

    border-radius: 8px;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        rgba(148,191,224,.07);

    border:
        1px solid
        rgba(148,191,224,.08);

    color: #7891a5;

    font-size: 8px;

    font-weight: 900;
}

.agent.running .agent-number {

    color: white;

    background:
        linear-gradient(
            145deg,
            #348cff,
            #43cfc2
        );

    border-color: transparent;
}

.agent.completed .agent-number {

    color: #7ce5ae;

    background:
        rgba(80,227,155,.10);

    border-color:
        rgba(80,227,155,.15);
}

.agent.error .agent-number {

    color: #ff8b98;

    background:
        rgba(255,110,125,.10);

    border-color:
        rgba(255,110,125,.17);
}

.agent-dot {

    width: 7px;
    height: 7px;

    border-radius: 50%;

    background: #3d5364;
}

.agent.running .agent-dot {

    background: var(--blue);

    box-shadow:
        0 0 0 5px
        rgba(89,185,255,.07);

    animation:
        pulse 1.1s infinite;
}

.agent.completed .agent-dot {

    background: var(--green);
}

.agent.error .agent-dot {

    background: var(--red);
}

.agent-name {

    margin-top: 12px;

    color: #dbe9f4;

    font-size: 10px;

    font-weight: 800;
}

.agent-status {

    margin-top: 4px;

    color: #617a8e;

    font-size: 8px;
}

.agent.running .agent-status {

    color: #7ecfff;
}

.agent.completed .agent-status {

    color: #71dca7;
}

.agent.error .agent-status {

    color: #ff8995;
}


/* ============================================================
   RESULT
   ============================================================ */

.result {

    margin-top: 20px;
}

.result-card {

    padding: 27px;

    border-radius: 24px;

    background:
        linear-gradient(
            145deg,
            rgba(16,38,60,.92),
            rgba(7,22,38,.90)
        );

    border:
        1px solid
        rgba(89,185,255,.15);

    box-shadow:
        var(--shadow);
}

.result-top {

    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 20px;
}

.result-label {

    color: #7894a9;

    font-size: 8px;

    font-weight: 900;

    letter-spacing: 1.4px;
}

.result-id {

    margin-top: 4px;

    font-size: 16px;

    font-weight: 900;
}

.decision-badge {

    padding: 10px 14px;

    border-radius: 999px;

    font-size: 9px;

    font-weight: 900;
}

.decision-approved {

    color: #75e2aa;

    background:
        rgba(80,227,155,.09);

    border:
        1px solid
        rgba(80,227,155,.17);
}

.decision-rejected {

    color: #ff8c99;

    background:
        rgba(255,110,125,.08);

    border:
        1px solid
        rgba(255,110,125,.16);
}

.decision-review {

    color: #f5ce7b;

    background:
        rgba(246,197,108,.08);

    border:
        1px solid
        rgba(246,197,108,.16);
}

.result-divider {

    height: 1px;

    background:
        rgba(148,191,224,.09);

    margin: 22px 0;
}

.result-grid {

    display: grid;

    grid-template-columns:
        repeat(4, minmax(0,1fr));

    gap: 10px;
}

.result-item {

    padding: 14px;

    border-radius: 13px;

    background:
        rgba(3,16,28,.54);

    border:
        1px solid
        rgba(148,191,224,.07);
}

.result-item span {

    display: block;

    color: #637b8e;

    font-size: 8px;

    margin-bottom: 5px;
}

.result-item strong {

    color: #dbeaf6;

    font-size: 10px;
}


/* ============================================================
   PDF
   ============================================================ */

.pdf-section {

    margin-top: 20px;
}

.pdf-toolbar {

    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 12px;

    padding: 15px 17px;

    border:
        1px solid
        rgba(89,185,255,.12);

    border-bottom: 0;

    border-radius:
        17px 17px 0 0;

    background:
        rgba(11,30,48,.92);
}

.pdf-title {

    font-size: 11px;

    font-weight: 850;
}

.pdf-sub {

    color: #627d91;

    font-size: 8px;

    margin-top: 3px;
}

.download-btn {

    padding: 9px 13px;

    border-radius: 10px;

    color: white;

    text-decoration: none;

    background:
        linear-gradient(
            100deg,
            #277eff,
            #45baff
        );

    font-size: 9px;

    font-weight: 850;
}

.pdf-frame {

    width: 100%;

    height: 760px;

    border:
        1px solid
        rgba(89,185,255,.12);

    border-radius:
        0 0 17px 17px;

    background: white;
}


/* ============================================================
   JSON
   ============================================================ */

details {

    margin-top: 20px;

    border:
        1px solid
        rgba(148,191,224,.10);

    border-radius: 17px;

    background:
        rgba(8,25,41,.78);

    overflow: hidden;
}

summary {

    cursor: pointer;

    padding: 15px;

    color: #b9cede;

    font-size: 10px;

    font-weight: 800;
}

pre {

    margin: 0;

    padding: 18px;

    max-height: 500px;

    overflow: auto;

    color: #9fd0ef;

    background:
        rgba(2,12,22,.65);

    font-size: 9px;

    line-height: 1.65;
}


/* ============================================================
   FOOTER
   ============================================================ */

.footer {

    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 20px;

    padding:
        30px 0 10px;

    margin-top: 55px;

    border-top:
        1px solid
        rgba(148,191,224,.08);

    color: #597286;

    font-size: 8px;
}

.footer strong {

    color: #9bb1c2;
}


/* ============================================================
   TOAST
   ============================================================ */

.toast {

    position: fixed;

    right: 22px;
    bottom: 22px;

    z-index: 999;

    max-width: 360px;

    padding: 13px 16px;

    border-radius: 14px;

    background:
        rgba(10,28,46,.94);

    border:
        1px solid
        rgba(89,185,255,.20);

    box-shadow:
        0 20px 50px
        rgba(0,0,0,.35);

    color: #dcecf7;

    font-size: 10px;

    transform:
        translateY(25px);

    opacity: 0;

    pointer-events: none;

    transition: .3s ease;
}

.toast.show {

    transform:
        translateY(0);

    opacity: 1;
}


/* ============================================================
   LOADING OVERLAY
   ============================================================ */

.processing-overlay {

    position: fixed;

    inset: 0;

    z-index: 9000;

    display: none;

    align-items: center;

    justify-content: center;

    background:
        rgba(2,9,17,.78);

    backdrop-filter:
        blur(12px);
}

.processing-overlay.show {

    display: flex;
}

.processing-box {

    width: min(430px, calc(100% - 35px));

    text-align: center;

    padding: 34px;

    border-radius: 25px;

    background:
        linear-gradient(
            145deg,
            rgba(16,42,67,.96),
            rgba(7,23,39,.96)
        );

    border:
        1px solid
        rgba(89,185,255,.22);

    box-shadow:
        0 35px 100px
        rgba(0,0,0,.48);
}

.processing-spinner {

    width: 70px;
    height: 70px;

    border-radius: 50%;

    margin: 0 auto 18px;

    border:
        2px solid
        rgba(89,185,255,.10);

    border-top-color:
        #58bbff;

    border-right-color:
        #55e0d0;

    animation:
        spinner 1s linear infinite;
}

@keyframes spinner {

    to {
        transform: rotate(360deg);
    }
}

.processing-title {

    font-size: 16px;

    font-weight: 900;
}

.processing-text {

    margin-top: 6px;

    color: var(--muted);

    font-size: 10px;

    line-height: 1.6;
}


/* ============================================================
   RESPONSIVE
   ============================================================ */

@media (max-width: 900px) {

    .hero {

        grid-template-columns: 1fr;

        padding-top: 50px;
    }

    .hero-visual {

        min-height: 320px;
    }

    .agent-grid {

        grid-template-columns:
            repeat(2, minmax(0,1fr));
    }

    .result-grid {

        grid-template-columns:
            repeat(2, minmax(0,1fr));
    }
}

@media (max-width: 650px) {

    .app {

        width:
            min(
                100% - 24px,
                1280px
            );
    }

    .topbar {

        min-height: 68px;
    }

    .online {

        display: none;
    }

    .hero {

        padding:
            38px 0 45px;
    }

    .hero h1 {

        font-size: 43px;

        letter-spacing: -2.5px;
    }

    .hero p {

        font-size: 12px;
    }

    .hero-stats {

        display: grid;

        grid-template-columns:
            repeat(3,1fr);

        gap: 6px;
    }

    .hero-stat {

        min-width: 0;

        padding: 10px 7px;
    }

    .hero-stat strong {

        font-size: 13px;
    }

    .hero-stat span {

        font-size: 6px;
    }

    .hero-visual {

        min-height: 280px;
    }

    .halo {

        width: 250px;
        height: 250px;
    }

    .house {

        transform:
            scale(.82)
            rotate(-3deg);
    }

    .form-grid {

        grid-template-columns: 1fr;
    }

    .field.full {

        grid-column: auto;
    }

    .card,
    .tracker-card,
    .result-card {

        padding: 18px;

        border-radius: 19px;
    }

    .section-title {

        font-size: 18px;
    }

    .tracker-head {

        flex-direction: column;
    }

    .agent-grid {

        grid-template-columns: 1fr;
    }

    .result-top {

        flex-direction: column;

        align-items: flex-start;
    }

    .result-grid {

        grid-template-columns: 1fr 1fr;
    }

    .pdf-frame {

        height: 560px;
    }

    .footer {

        flex-direction: column;

        text-align: center;
    }
}

@media (max-width: 420px) {

    .hero h1 {

        font-size: 38px;
    }

    .start-title {

        font-size: 43px;

        letter-spacing: -2px;
    }

    .hero-stats {

        grid-template-columns: 1fr;
    }

    .result-grid {

        grid-template-columns: 1fr;
    }
}


/* ============================================================
   CINEMATIC UI ENHANCEMENTS — VISUAL ONLY
   ============================================================ */

body::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: 9997;
    pointer-events: none;
    background:
        radial-gradient(circle at var(--mx,50%) var(--my,50%), rgba(95,205,255,.07), transparent 22%),
        radial-gradient(circle at 50% 50%, transparent 45%, rgba(0,0,0,.34) 100%);
    mix-blend-mode: screen;
    opacity: .8;
}

body::after {
    content: "";
    position: fixed;
    inset: 0;
    z-index: 9996;
    pointer-events: none;
    background: repeating-linear-gradient(
        to bottom,
        rgba(255,255,255,.018) 0px,
        rgba(255,255,255,.018) 1px,
        transparent 1px,
        transparent 5px
    );
    opacity: .22;
}

.cinematic-cursor {
    position: fixed; left:0; top:0; width:7px; height:7px; border-radius:50%;
    pointer-events:none; z-index:10000; transform:translate3d(-100px,-100px,0);
    background:rgba(145,225,255,.95);
    box-shadow:0 0 7px rgba(89,185,255,.75),0 0 15px rgba(89,185,255,.28);
    opacity:.92; contain:layout style paint; will-change:transform;
    transition:width .18s ease,height .18s ease,box-shadow .18s ease;
}
.cinematic-cursor.hover { width:10px; height:10px; background:#b4f5ff;
    box-shadow:0 0 8px rgba(85,224,208,.8),0 0 18px rgba(85,224,208,.32); }
.cinematic-cursor-bubble {
    position:fixed; left:0; top:0; width:var(--bubble-size,4px); height:var(--bubble-size,4px);
    border-radius:50%; pointer-events:none; z-index:9999;
    background:rgba(130,215,255,.72); box-shadow:0 0 7px rgba(89,185,255,.28);
    transform:translate3d(-50%,-50%,0); animation:cursorBubbleFloat var(--bubble-life,900ms) ease-out forwards;
    will-change:transform,opacity;
}
@keyframes cursorBubbleFloat {
    0%{opacity:.62;transform:translate3d(-50%,-50%,0) scale(.7)}
    100%{opacity:0;transform:translate3d(calc(-50% + var(--bubble-drift-x,0px)),calc(-50% + var(--bubble-drift-y,-18px)),0) scale(1.15)}
}
.cinematic-particles { position:fixed; inset:0; z-index:-5; pointer-events:none; overflow:hidden; contain:strict; }
.cinematic-particle {
    position:absolute; width:1.5px; height:1.5px; border-radius:50%;
    background:rgba(145,220,255,.48); opacity:.35;
}
/* Performance version: particles are static, sparse and barely visible. */
.cinematic-light-sweep {
    position:fixed; inset:0; z-index:-4; pointer-events:none;
    background:radial-gradient(circle at 20% 30%,rgba(89,185,255,.035),transparent 28%),
               radial-gradient(circle at 80% 70%,rgba(85,224,208,.025),transparent 30%);
    opacity:.9; contain:paint;
}

.start-screen::before {
    content: "";
    position: absolute;
    inset: 0;
    background:
        radial-gradient(ellipse at 50% 58%, rgba(63,161,255,.11), transparent 25%),
        linear-gradient(to bottom, rgba(0,0,0,.15), transparent 35%, rgba(0,0,0,.4));
    pointer-events: none;
}

.start-screen::after {
    content: "";
    position: absolute;
    width: min(900px, 110vw);
    height: 180px;
    left: 50%;
    bottom: -85px;
    transform: translateX(-50%);
    background: radial-gradient(ellipse, rgba(74,184,255,.18), transparent 68%);
    filter: blur(16px);
    pointer-events: none;
    animation: cinematicGroundPulse 4.5s ease-in-out infinite;
}

@keyframes cinematicGroundPulse {
    0%,100% { opacity: .45; transform: translateX(-50%) scaleX(.92); }
    50% { opacity: .9; transform: translateX(-50%) scaleX(1.08); }
}

.start-content {
    animation: cinematicArrival 1.15s cubic-bezier(.2,.8,.2,1) both;
}

@keyframes cinematicArrival {
    from { opacity: 0; transform: translateY(28px) scale(.97); filter: blur(8px); }
    to { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
}

.start-orbit {
    filter: drop-shadow(0 0 25px rgba(89,185,255,.12));
}

.start-core {
    position: relative;
    animation: coreCinematicPulse 3.2s ease-in-out infinite;
}

.start-core::before,
.start-core::after {
    content: "";
    position: absolute;
    border-radius: 50%;
    inset: -10px;
    border: 1px solid rgba(100,210,255,.12);
    animation: coreRing 3.5s ease-out infinite;
}

.start-core::after { animation-delay: 1.75s; }

@keyframes coreRing {
    0% { transform: scale(.72); opacity: .7; }
    100% { transform: scale(1.65); opacity: 0; }
}

@keyframes coreCinematicPulse {
    0%,100% { box-shadow: 0 0 60px rgba(49,137,255,.20), inset 0 1px 0 rgba(255,255,255,.08); }
    50% { box-shadow: 0 0 85px rgba(49,137,255,.34), 0 0 130px rgba(85,224,208,.08), inset 0 1px 0 rgba(255,255,255,.1); }
}

.house {
    transform-style: preserve-3d;
    will-change: transform;
    box-shadow: 0 35px 80px rgba(0,0,0,.35), 0 0 55px rgba(58,167,255,.08), inset 0 1px 0 rgba(255,255,255,.08);
}

.house::before {
    content: "";
    position: absolute;
    left: 20px;
    right: 20px;
    bottom: -24px;
    height: 32px;
    border-radius: 50%;
    background: radial-gradient(ellipse, rgba(58,171,255,.2), transparent 70%);
    filter: blur(7px);
    animation: houseGroundGlow 3.8s ease-in-out infinite;
}

@keyframes houseGroundGlow {
    0%,100% { opacity: .45; transform: scaleX(.82); }
    50% { opacity: .95; transform: scaleX(1.12); }
}

.door {
    /* CLOSED by default. It opens only while the pointer is over it. */
    transform-origin: left center;
    transform: rotateY(0deg) translateZ(0);
    backface-visibility: visible;
    transform-style: preserve-3d;
    transition: transform 900ms cubic-bezier(.22,.78,.18,1), filter 650ms ease, box-shadow 650ms ease;
    will-change: transform;
    z-index: 4;
    box-shadow: inset 0 0 0 rgba(106,215,255,0);
}

.door::before {
    content: "";
    position: absolute;
    inset: 5px 4px 4px;
    border-radius: 4px;
    background: linear-gradient(135deg, rgba(112,211,255,.12), transparent 50%);
    opacity: 0;
    transition: opacity .7s ease;
}

.door::after {
    content: "";
    position: absolute;
    width: 7px;
    height: 11px;
    border-radius: 4px;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
    background: radial-gradient(circle at 50% 62%, #5a3b0a 0 1.3px, transparent 1.5px), linear-gradient(#ffe08a, #d99d25);
    box-shadow: 0 0 7px rgba(246,197,108,.82), 0 0 14px rgba(246,197,108,.35);
}

/* Fixed door hit area: stays locked to the doorway even while the door swings open. */
.door-hit-area {
    position: absolute;
    width: 39px;
    height: 60px;
    right: 18px;
    bottom: -3px;
    z-index: 10;
    cursor: pointer;
    pointer-events: auto;
}

.door-hit-area .door {
    inset: auto;
    right: 5px;
    bottom: 3px;
    width: 29px;
    height: 52px;
    pointer-events: none;
}

.door-hit-area::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    bottom: 0;
    border-radius: 8px 8px 2px 2px;
    pointer-events: none;
}

/* Door approach glow: stays visible before the pointer reaches the door. */
.house-body::before {
    content: "";
    position: absolute;
    width: 18px;
    height: 18px;
    right: 28px;
    bottom: 42px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,220,108,.98) 0%, rgba(246,197,108,.42) 34%, rgba(246,197,108,0) 72%);
    box-shadow: 0 0 16px rgba(246,197,108,.48), 0 0 34px rgba(246,197,108,.22);
    opacity: .72;
    pointer-events: none;
    z-index: 8;
    animation: doorBeacon 1.7s ease-in-out infinite;
}

.house-body::after {
    content: "";
    position: absolute;
    width: 58px;
    height: 58px;
    right: 8px;
    bottom: 21px;
    border-radius: 50%;
    border: 1px solid rgba(246,197,108,.25);
    box-shadow: 0 0 24px rgba(246,197,108,.16), inset 0 0 20px rgba(246,197,108,.08);
    opacity: .55;
    pointer-events: none;
    z-index: 7;
    animation: doorBeaconRing 2.4s ease-out infinite;
}

@keyframes doorBeacon {
    0%, 100% { transform: scale(.72); opacity: .38; filter: blur(.2px); }
    50% { transform: scale(1.2); opacity: .95; filter: blur(0); }
}

@keyframes doorBeaconRing {
    0% { transform: scale(.45); opacity: .05; }
    35% { opacity: .55; }
    100% { transform: scale(1.45); opacity: 0; }
}

.house.door-approach .house-body::before {
    animation-duration: .9s;
    opacity: 1;
    box-shadow: 0 0 24px rgba(255,216,105,.90), 0 0 54px rgba(246,197,108,.34);
}

.house.door-approach .house-body::after {
    animation-duration: 1.15s;
    border-color: rgba(246,197,108,.55);
    opacity: .95;
}

.house-body {
    perspective: 520px;
    perspective-origin: 78% 50%;
    transform-style: preserve-3d;
}

.house.door-hover .door {
    transform: rotateY(-105deg) translateX(-3px) translateZ(2px);
    filter: brightness(1.28) saturate(1.15);
    box-shadow: -12px 0 28px rgba(246,197,108,.48);
}

.house.door-hover .door::after {
    background: #ffe08a;
    box-shadow: 0 0 10px rgba(255,216,105,.95), 0 0 20px rgba(246,197,108,.65);
}

.house.door-hover .door::before {
    opacity: 1;
}

.house.door-hover .house-body::after {
    opacity: 1;
    animation: doorwayReveal .65s ease-out both;
}

.house.door-hover .house-body::after {
    content: "";
    position: absolute;
    width: 22px;
    height: 42px;
    right: 27px;
    bottom: 3px;
    border-radius: 5px 5px 1px 1px;
    background: linear-gradient(to bottom, rgba(255,226,132,.98), rgba(246,197,108,.42));
    box-shadow: 0 0 28px rgba(246,197,108,.70), 0 0 65px rgba(246,197,108,.28);
    animation: doorwayReveal 1.15s ease-out both;
    z-index: 2;
}

@keyframes doorwayReveal {
    from { opacity: 0; transform: scaleY(.65); filter: blur(5px); }
    to { opacity: 1; transform: scaleY(1); filter: blur(0); }
}

.start-screen.cinematic-exit {
    animation: cinematicExit .95s cubic-bezier(.76,0,.24,1) both;
}

.start-screen.cinematic-exit .start-content {
    animation: cinematicExitContent .75s cubic-bezier(.76,0,.24,1) both;
}

@keyframes cinematicExit {
    0% { opacity: 1; filter: brightness(1); }
    55% { opacity: 1; filter: brightness(1.18); }
    100% { opacity: 0; filter: brightness(1.8) blur(4px); visibility: hidden; }
}

@keyframes cinematicExitContent {
    to { transform: scale(1.06) translateY(-8px); opacity: 0; filter: blur(7px); }
}

.cinematic-flash {
    position: fixed;
    inset: 0;
    z-index: 10001;
    pointer-events: none;
    background: radial-gradient(circle at 50% 50%, rgba(188,239,255,.24), rgba(88,190,255,.08) 25%, transparent 58%);
    opacity: 0;
}

.cinematic-flash.active { animation: cinematicFlash .9s ease-out both; }

@keyframes cinematicFlash {
    0% { opacity: 0; }
    18% { opacity: .75; }
    100% { opacity: 0; }
}

@media (pointer: coarse) {
    .cinematic-cursor { display: none; }
}

@media (prefers-reduced-motion: reduce) {
    .house-body::before,
    .house-body::after { animation: none !important; }
    .cinematic-particle,
    .cinematic-light-sweep,
    .start-content,
    .start-core,
    .house::before { animation: none !important; }
    .door { transition-duration: .2s; }
}

</style>

</head>


<body>


<div class="cinematic-particles" id="cinematicParticles"></div>
<div class="cinematic-light-sweep"></div>
<div class="cinematic-cursor" id="cinematicCursor"></div>
<div class="cinematic-flash" id="cinematicFlash"></div>


<!-- ========================================================
     BACKGROUND
     ======================================================== -->

<div class="background">

    <div class="grid"></div>

    <div class="orb one"></div>

    <div class="orb two"></div>

    <div class="orb three"></div>

</div>


<!-- ========================================================
     START SCREEN
     ======================================================== -->

<div
    id="startScreen"
    class="start-screen"
>

    <div class="start-content">

        <div class="start-orbit">

            <div class="start-core">
                <span>GA</span>
            </div>

        </div>

        <div class="start-kicker">
            <i></i>
            AI-POWERED MORTGAGE PLATFORM
        </div>

        <h1 class="start-title">
            <span>Gen AI Mortgage</span>
            <span>Loan Application</span>
        </h1>

        <p class="start-subtitle">

            Intelligent document processing,
            verification, underwriting, risk analysis
            and loan decisioning powered by an
            11-agent AI workflow.

        </p>

        <button
            id="enterBtn"
            class="enter-btn"
        >
            Enter Application →
        </button>

    </div>

</div>


<!-- ========================================================
     PROCESSING OVERLAY
     ======================================================== -->

<div
    id="processingOverlay"
    class="processing-overlay"
>

    <div class="processing-box">

        <div class="processing-spinner"></div>

        <div class="processing-title">
            AI Loan Processing
        </div>

        <div
            id="processingText"
            class="processing-text"
        >
            Initializing the mortgage intelligence workflow...
        </div>

    </div>

</div>


<!-- ========================================================
     MAIN APP
     ======================================================== -->

<main
    id="mainApp"
    class="app"
    style="display:none;"
>


<!-- ========================================================
     TOPBAR
     ======================================================== -->

<header class="topbar">

    <div class="brand">

        <div class="brand-logo">
            <span>GA</span>
        </div>

        <div>

            <div class="brand-name">
                Gen<span>AI</span> Mortgage
            </div>

            <div class="brand-sub">
                INTELLIGENT LOAN PROCESSING
            </div>

        </div>

    </div>


    <div class="online">

        <span class="online-dot"></span>

        AI SYSTEM ONLINE

    </div>

    <a href="/manager" style="margin-left:14px;display:inline-flex;align-items:center;gap:7px;padding:10px 14px;border-radius:12px;border:1px solid rgba(125,211,252,.28);background:rgba(15,35,58,.72);color:#dff7ff;text-decoration:none;font-size:11px;font-weight:800;letter-spacing:.8px;">▦ MANAGER</a>

</header>


<!-- ========================================================
     HERO
     ======================================================== -->

<section class="hero">

    <div>

        <div class="hero-kicker">
            11-AGENT AI LENDING WORKFLOW
        </div>

        <h1>
            Smarter mortgage
            <span>decisions.</span>
        </h1>

        <p>

            Enter the applicant profile, financial details
            and supporting documents. The AI workflow
            automatically processes the application from
            document intake through final loan resolution.

        </p>

        <div class="hero-stats">

            <div class="hero-stat">
                <strong>11</strong>
                <span>AI AGENTS</span>
            </div>

            <div class="hero-stat">
                <strong>01</strong>
                <span>UNIFIED WORKFLOW</span>
            </div>

            <div class="hero-stat">
                <strong>24/7</strong>
                <span>AUTOMATED REVIEW</span>
            </div>

        </div>

    </div>


    <div class="hero-visual">

        <div class="halo"></div>

        <div class="house">

            <div class="roof"></div>

            <div class="house-body">

                <div class="window"></div>

                <div class="door-hit-area" aria-label="Interactive house door">
                    <div class="door"></div>
                </div>

            </div>

        </div>

    </div>

</section>


<!-- ========================================================
     APPLICANT
     ======================================================== -->

<section class="section">

    <div class="section-head">

        <div class="section-number">
            01
        </div>

        <div>

            <div class="section-kicker">
                APPLICATION PROFILE
            </div>

            <div class="section-title">
                Applicant Information
            </div>

            <div class="section-description">
                Basic applicant identity and contact information.
            </div>

        </div>

    </div>


    <div class="card">

        <div class="form-grid">

            <div class="field">

                <label>Full Name</label>

                <input
                    id="full_name"
                    type="text"
                    placeholder="Enter full name"
                >

            </div>


            <div class="field">

                <label>Date of Birth</label>

                <input
                    id="date_of_birth"
                    type="date"
                >

            </div>


            <div class="field">

                <label>PAN Number</label>

                <input
                    id="pan"
                    type="text"
                    placeholder="ABCDE1234F"
                    maxlength="10"
                >

            </div>


            <div class="field">

                <label>Mobile Number</label>

                <input
                    id="mobile"
                    type="tel"
                    placeholder="10 digit mobile number"
                >

            </div>


            <div class="field">

                <label>Email</label>

                <input
                    id="email"
                    type="email"
                    placeholder="example@email.com"
                >

            </div>


            <div class="field">

                <label>Employer</label>

                <input
                    id="employer"
                    type="text"
                    placeholder="Company / Employer"
                >

            </div>


            <div class="field full">

                <label>Residential Address</label>

                <textarea
                    id="address"
                    placeholder="Complete residential address"
                ></textarea>

            </div>

        </div>

    </div>

</section>


<!-- ========================================================
     EMPLOYMENT
     ======================================================== -->

<section class="section">

    <div class="section-head">

        <div class="section-number">
            02
        </div>

        <div>

            <div class="section-kicker">
                FINANCIAL PROFILE
            </div>

            <div class="section-title">
                Employment & Income
            </div>

            <div class="section-description">
                Current employment and income profile used by underwriting.
            </div>

        </div>

    </div>


    <div class="card">

        <div class="form-grid">

            <div class="field">

                <label>Years of Experience</label>

                <input
                    id="years_of_experience"
                    type="number"
                    min="0"
                    step="0.1"
                    value="0"
                >

            </div>


            <div class="field">

                <label>Current Employment Years</label>

                <input
                    id="current_employment_years"
                    type="number"
                    min="0"
                    step="0.1"
                    value="0"
                >

            </div>


            <div class="field">

                <label>Gross Monthly Income (₹)</label>

                <input
                    id="gross_monthly_income"
                    type="number"
                    min="0"
                    step="1000"
                    value="0"
                >

            </div>


            <div class="field">

                <label>Net Monthly Income (₹)</label>

                <input
                    id="net_monthly_income"
                    type="number"
                    min="0"
                    step="1000"
                    value="0"
                >

            </div>


            <div class="field">

                <label>Existing Monthly EMI (₹)</label>

                <input
                    id="existing_monthly_emi"
                    type="number"
                    min="0"
                    step="1000"
                    value="0"
                >

            </div>

        </div>

    </div>

</section>


<!-- ========================================================
     LOAN
     ======================================================== -->

<section class="section">

    <div class="section-head">

        <div class="section-number">
            03
        </div>

        <div>

            <div class="section-kicker">
                LOAN CONFIGURATION
            </div>

            <div class="section-title">
                Loan & Property Details
            </div>

            <div class="section-description">
                Configure the requested mortgage and property information.
            </div>

        </div>

    </div>


    <div class="card">

        <div class="form-grid">


            <div class="field">

                <label>
                    Requested Loan Amount (₹)
                </label>

                <input
                    id="requested_loan_amount"
                    type="number"
                    min="0"
                    step="10000"
                    value="0"
                >

            </div>


            <div class="field">

                <label>
                    Loan Tenure (Years)
                </label>

                <input
                    id="loan_tenure_years"
                    type="number"
                    min="1"
                    step="1"
                    value="20"
                >

            </div>


            <div class="field">

                <label>
                    Interest Rate (%)
                </label>

                <input
                    id="interest_rate"
                    type="number"
                    min="0"
                    step="0.01"
                    value="8.5"
                >

            </div>


            <!-- IMPORTANT:
                 This is TEXT/SELECT.
                 NEVER converted to float.
            -->

            <div class="field">

                <label>
                    Loan Purpose
                </label>

                <select id="loan_purpose">

                    <option value="Property Purchase">
                        Property Purchase
                    </option>

                    <option value="Home Construction">
                        Home Construction
                    </option>

                    <option value="Home Renovation">
                        Home Renovation
                    </option>

                    <option value="Balance Transfer">
                        Balance Transfer
                    </option>

                    <option value="Plot Purchase">
                        Plot Purchase
                    </option>

                </select>

            </div>


            <div class="field">

                <label>
                    Property Value (₹)
                </label>

                <input
                    id="property_value"
                    type="number"
                    min="0"
                    step="10000"
                    value="0"
                >

            </div>


        </div>

    </div>

</section>


<!-- ========================================================
     DOCUMENTS
     ======================================================== -->

<section class="section">

    <div class="section-head">

        <div class="section-number">
            04
        </div>

        <div>

            <div class="section-kicker">
                DOCUMENT INTELLIGENCE
            </div>

            <div class="section-title">
                Loan Documents
            </div>

            <div class="section-description">
                Upload PDF documents for AI-powered intake and verification.
            </div>

        </div>

    </div>


    <div class="card">

        <div
            id="uploadBox"
            class="upload-box"
        >

            <div class="upload-icon">
                ↑
            </div>

            <div class="upload-title">
                Drop your loan documents here
            </div>

            <div class="upload-sub">
                Upload Aadhaar, PAN, salary slips, bank statements,
                property documents and other PDFs.
            </div>

            <div class="upload-badge">
                PDF DOCUMENTS
            </div>

            <input
                id="documents"
                type="file"
                accept=".pdf,application/pdf"
                multiple
                hidden
            >

            <div
                id="fileList"
                class="file-list"
            ></div>

        </div>


        <div class="action-card">

            <div class="action-top">

                <div class="action-icon">
                    ✦
                </div>

                <div>

                    <div class="action-title">
                        Ready to process the application?
                    </div>

                    <div class="action-sub">
                        All 11 AI agents will execute automatically.
                    </div>

                </div>

            </div>


            <button
                id="processBtn"
                class="process-btn"
            >
                Start AI Loan Processing →
            </button>


            <button
                id="newBtn"
                class="new-btn"
            >
                ↻ Start New Application
            </button>


            <div class="secure">
                ● Secure AI loan processing workflow
            </div>

        </div>

    </div>

</section>


<!-- ========================================================
     AI TRACKER
     ======================================================== -->

<section class="section">

    <div class="section-head">

        <div class="section-number">
            05
        </div>

        <div>

            <div class="section-kicker">
                AUTOMATED DECISION ENGINE
            </div>

            <div class="section-title">
                AI Processing Pipeline
            </div>

            <div class="section-description">
                Watch the complete mortgage workflow execute in real time.
            </div>

        </div>

    </div>


    <div class="tracker-card">

        <div class="tracker-head">

            <div>

                <div class="tracker-kicker">
                    LIVE AGENT ORCHESTRATION
                </div>

                <div class="tracker-title">
                    11-Agent Mortgage Intelligence
                </div>

                <div
                    id="trackerMessage"
                    class="tracker-desc"
                >
                    Ready to process application
                </div>

            </div>


            <div
                id="trackerStatus"
                class="tracker-status"
            >
                READY
            </div>

        </div>


        <div class="progress-wrap">

            <div class="progress-line">

                <span>
                    Processing Progress
                </span>

                <strong>
                    <span id="progressCount">0</span> / 11
                </strong>

            </div>


            <div class="progress-bar">

                <div
                    id="progressFill"
                    class="progress-fill"
                ></div>

            </div>

        </div>


        <div class="current-agent">

            <div class="current-icon">
                ✦
            </div>

            <div class="current-info">

                <div class="current-label">
                    CURRENT AI AGENT
                </div>

                <div
                    id="currentAgent"
                    class="current-name"
                >
                    Waiting to start
                </div>

            </div>

            <div
                id="currentCount"
                class="current-count"
            >
                0 / 11
            </div>

        </div>


        <div
            id="agentGrid"
            class="agent-grid"
        >

        </div>

    </div>

</section>


<!-- ========================================================
     RESULT
     ======================================================== -->

<section
    id="resultSection"
    class="section result"
    style="display:none;"
>

    <div class="section-head">

        <div class="section-number">
            06
        </div>

        <div>

            <div class="section-kicker">
                DECISION OUTPUT
            </div>

            <div class="section-title">
                Final Loan Decision
            </div>

            <div class="section-description">
                Completed AI assessment and application outcome.
            </div>

        </div>

    </div>


    <div class="result-card">

        <div class="result-top">

            <div>

                <div class="result-label">
                    APPLICATION
                </div>

                <div
                    id="resultApplicationId"
                    class="result-id"
                >
                    Loan Application
                </div>

            </div>


            <div
                id="decisionBadge"
                class="decision-badge decision-review"
            >
                PROCESSING
            </div>

        </div>


        <div class="result-divider"></div>


        <div class="result-grid">

            <div class="result-item">

                <span>
                    Applicant
                </span>

                <strong
                    id="resultApplicant"
                >
                    —
                </strong>

            </div>


            <div class="result-item">

                <span>
                    Decision
                </span>

                <strong
                    id="resultDecision"
                >
                    —
                </strong>

            </div>


            <div class="result-item">

                <span>
                    AI Workflow
                </span>

                <strong>
                    11 Agents
                </strong>

            </div>


            <div class="result-item">

                <span>
                    Status
                </span>

                <strong
                    id="resultStatus"
                >
                    Completed
                </strong>

            </div>

        </div>

    </div>


    <!-- PDF -->

    <div class="pdf-section">

        <div class="pdf-toolbar">

            <div>

                <div class="pdf-title">
                    Generated Loan Assessment Report
                </div>

                <div class="pdf-sub">
                    AI-generated mortgage processing report
                </div>

            </div>


            <a
                id="downloadBtn"
                class="download-btn"
                href="#"
                style="display:none;"
            >
                ↓ Download PDF
            </a>

        </div>


        <iframe
            id="pdfFrame"
            class="pdf-frame"
            style="display:none;"
        ></iframe>

    </div>


    <!-- TECHNICAL -->

    <details>

        <summary>
            Technical Processing Data
        </summary>

        <pre id="jsonOutput">{}</pre>

    </details>

</section>


<!-- ========================================================
     FOOTER
     ======================================================== -->

<footer class="footer">

    <div>
        <strong>Gen AI Mortgage</strong>
        · Intelligent Loan Processing
    </div>

    <div>
        Document AI · Verification · Underwriting · Risk · Decisioning
    </div>

</footer>


</main>


<!-- ========================================================
     TOAST
     ======================================================== -->

<div
    id="toast"
    class="toast"
></div>


<script>


// ============================================================
// GLOBAL STATE
// ============================================================

let currentJobId = null;

let pollingTimer = null;

let selectedFiles = [];


// ============================================================
// ELEMENTS
// ============================================================

const startScreen =
    document.getElementById("startScreen");

const mainApp =
    document.getElementById("mainApp");

const enterBtn =
    document.getElementById("enterBtn");

const processBtn =
    document.getElementById("processBtn");

const newBtn =
    document.getElementById("newBtn");

const documents =
    document.getElementById("documents");

const uploadBox =
    document.getElementById("uploadBox");

const fileList =
    document.getElementById("fileList");

const processingOverlay =
    document.getElementById("processingOverlay");

const processingText =
    document.getElementById("processingText");


// ============================================================
// START SCREEN
// ============================================================

enterBtn.addEventListener(
    "click",
    function() {

        startScreen.classList.add("hide");

        mainApp.style.display = "block";

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

    }
);


// ============================================================
// UPLOAD BOX
// ============================================================

uploadBox.addEventListener(
    "click",
    function(event) {

        if (event.target === documents) {
            return;
        }

        documents.click();

    }
);


documents.addEventListener(
    "change",
    function() {

        selectedFiles =
            Array.from(documents.files || []);

        renderFiles();

    }
);


// ============================================================
// DRAG & DROP
// ============================================================

uploadBox.addEventListener(
    "dragover",
    function(event) {

        event.preventDefault();

        uploadBox.style.borderColor =
            "rgba(89,185,255,.65)";

    }
);


uploadBox.addEventListener(
    "dragleave",
    function() {

        uploadBox.style.borderColor =
            "rgba(89,185,255,.28)";

    }
);


uploadBox.addEventListener(
    "drop",
    function(event) {

        event.preventDefault();

        const files =
            Array.from(
                event.dataTransfer.files || []
            ).filter(
                file =>
                    file.name
                    .toLowerCase()
                    .endsWith(".pdf")
            );

        selectedFiles = files;

        renderFiles();

    }
);


// ============================================================
// RENDER FILES
// ============================================================

function renderFiles() {

    if (!selectedFiles.length) {

        fileList.style.display = "none";

        fileList.innerHTML = "";

        return;
    }

    fileList.style.display = "block";

    fileList.innerHTML =
        selectedFiles.map(
            function(file) {

                return `
                    <div class="file-item">
                        <span>${escapeHtml(file.name)}</span>
                        <span>PDF</span>
                    </div>
                `;

            }
        ).join("");

}


// ============================================================
// AGENT UI
// ============================================================

function initializeAgents() {

    const grid =
        document.getElementById(
            "agentGrid"
        );

    grid.innerHTML =
        AGENT_DATA.map(
            function(agent) {

                return `
                    <div
                        class="agent"
                        id="agent-${agent.id}"
                    >

                        <div class="agent-top">

                            <div class="agent-number">
                                ${agent.id}
                            </div>

                            <div class="agent-dot"></div>

                        </div>

                        <div class="agent-name">
                            ${agent.name}
                        </div>

                        <div
                            class="agent-status"
                            id="agent-status-${agent.id}"
                        >
                            Waiting
                        </div>

                    </div>
                `;

            }
        ).join("");

}


// ============================================================
// AGENT DATA
// ============================================================

const AGENT_DATA = [
    {
        id: 1,
        name: "Document Intake"
    },
    {
        id: 2,
        name: "Document Checklist"
    },
    {
        id: 3,
        name: "Data Extraction"
    },
    {
        id: 4,
        name: "Document Verification"
    },
    {
        id: 5,
        name: "Loan Underwriting"
    },
    {
        id: 6,
        name: "Risk & Fraud"
    },
    {
        id: 7,
        name: "AI Case Summary"
    },
    {
        id: 8,
        name: "Final Decision"
    },
    {
        id: 9,
        name: "Human Review"
    },
    {
        id: 10,
        name: "Reviewer Resolution"
    },
    {
        id: 11,
        name: "Final Resolution"
    }
];

initializeAgents();


// ============================================================
// UPDATE AGENTS
// ============================================================

function updateAgents(agents) {

    if (!Array.isArray(agents)) {
        return;
    }

    agents.forEach(
        function(agent) {

            const card =
                document.getElementById(
                    "agent-" + agent.id
                );

            const status =
                document.getElementById(
                    "agent-status-" + agent.id
                );

            if (!card || !status) {
                return;
            }

            card.classList.remove(
                "running",
                "completed",
                "error"
            );

            if (agent.status === "running") {

                card.classList.add("running");

                status.textContent =
                    "Processing";

            }

            else if (
                agent.status === "completed"
            ) {

                card.classList.add("completed");

                status.textContent =
                    "Completed";

            }

            else if (
                agent.status === "error"
            ) {

                card.classList.add("error");

                status.textContent =
                    "Error";

            }

            else {

                status.textContent =
                    "Waiting";

            }

        }
    );

}


// ============================================================
// TOAST
// ============================================================

function showToast(message) {

    const toast =
        document.getElementById("toast");

    toast.textContent = message;

    toast.classList.add("show");

    setTimeout(
        function() {

            toast.classList.remove("show");

        },
        3500
    );

}


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}


// ============================================================
// GET FIELD
// ============================================================

function valueOf(id) {

    const element =
        document.getElementById(id);

    return element
        ? element.value
        : "";

}


// ============================================================
// RESET APPLICATION
// ============================================================

newBtn.addEventListener(
    "click",
    function() {

        resetApplication();

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

    }
);


function resetApplication() {

    const ids = [
        "full_name",
        "date_of_birth",
        "pan",
        "mobile",
        "email",
        "address",
        "employer"
    ];

    ids.forEach(
        function(id) {

            const el =
                document.getElementById(id);

            if (el) {
                el.value = "";
            }

        }
    );


    document.getElementById(
        "years_of_experience"
    ).value = "0";

    document.getElementById(
        "current_employment_years"
    ).value = "0";

    document.getElementById(
        "gross_monthly_income"
    ).value = "0";

    document.getElementById(
        "net_monthly_income"
    ).value = "0";

    document.getElementById(
        "existing_monthly_emi"
    ).value = "0";

    document.getElementById(
        "requested_loan_amount"
    ).value = "0";

    document.getElementById(
        "loan_tenure_years"
    ).value = "20";

    document.getElementById(
        "interest_rate"
    ).value = "8.5";

    document.getElementById(
        "loan_purpose"
    ).value = "Property Purchase";

    document.getElementById(
        "property_value"
    ).value = "0";


    selectedFiles = [];

    documents.value = "";

    renderFiles();


    currentJobId = null;


    document.getElementById(
        "resultSection"
    ).style.display = "none";


    document.getElementById(
        "pdfFrame"
    ).style.display = "none";


    document.getElementById(
        "downloadBtn"
    ).style.display = "none";


    document.getElementById(
        "jsonOutput"
    ).textContent = "{}";


    resetTracker();


    showToast(
        "New application ready"
    );

}


// ============================================================
// RESET TRACKER
// ============================================================

function resetTracker() {

    document.getElementById(
        "progressFill"
    ).style.width = "0%";

    document.getElementById(
        "progressCount"
    ).textContent = "0";

    document.getElementById(
        "currentCount"
    ).textContent = "0 / 11";

    document.getElementById(
        "currentAgent"
    ).textContent =
        "Waiting to start";

    document.getElementById(
        "trackerMessage"
    ).textContent =
        "Ready to process application";

    document.getElementById(
        "trackerStatus"
    ).textContent =
        "READY";

    initializeAgents();

}


// ============================================================
// PROCESS BUTTON
// ============================================================

processBtn.addEventListener(
    "click",
    startProcessing
);


// ============================================================
// VALIDATION
// ============================================================

function validateForm() {

    const required = [
        ["full_name", "Full Name"],
        ["date_of_birth", "Date of Birth"],
        ["pan", "PAN Number"],
        ["mobile", "Mobile Number"],
        ["email", "Email"],
        ["address", "Residential Address"],
        ["employer", "Employer"]
    ];

    for (
        const item of required
    ) {

        const element =
            document.getElementById(
                item[0]
            );

        if (
            !element ||
            !String(element.value).trim()
        ) {

            showToast(
                item[1] +
                " is required"
            );

            element?.focus();

            return false;

        }

    }


    const requested =
        Number(
            valueOf(
                "requested_loan_amount"
            )
        );

    const property =
        Number(
            valueOf(
                "property_value"
            )
        );


    if (
        !Number.isFinite(requested) ||
        requested <= 0
    ) {

        showToast(
            "Enter a valid requested loan amount"
        );

        return false;

    }


    if (
        !Number.isFinite(property) ||
        property <= 0
    ) {

        showToast(
            "Enter a valid property value"
        );

        return false;

    }


    return true;

}


// ============================================================
// START PROCESSING
// ============================================================

async function startProcessing() {

    if (!validateForm()) {
        return;
    }


    processBtn.disabled = true;

    processingOverlay.classList.add(
        "show"
    );


    processingText.textContent =
        "Uploading documents and initializing AI agents...";


    resetTracker();


    // --------------------------------------------------------
    // FORM DATA
    // --------------------------------------------------------

    const formData =
        new FormData();


    formData.append(
        "full_name",
        valueOf("full_name")
    );

    formData.append(
        "date_of_birth",
        valueOf("date_of_birth")
    );

    formData.append(
        "pan",
        valueOf("pan")
    );

    formData.append(
        "mobile",
        valueOf("mobile")
    );

    formData.append(
        "email",
        valueOf("email")
    );

    formData.append(
        "address",
        valueOf("address")
    );

    formData.append(
        "employer",
        valueOf("employer")
    );

    formData.append(
        "years_of_experience",
        valueOf("years_of_experience")
    );

    formData.append(
        "current_employment_years",
        valueOf(
            "current_employment_years"
        )
    );

    formData.append(
        "gross_monthly_income",
        valueOf(
            "gross_monthly_income"
        )
    );

    formData.append(
        "net_monthly_income",
        valueOf(
            "net_monthly_income"
        )
    );

    formData.append(
        "existing_monthly_emi",
        valueOf(
            "existing_monthly_emi"
        )
    );

    formData.append(
        "requested_loan_amount",
        valueOf(
            "requested_loan_amount"
        )
    );

    formData.append(
        "loan_tenure_years",
        valueOf(
            "loan_tenure_years"
        )
    );

    formData.append(
        "interest_rate",
        valueOf(
            "interest_rate"
        )
    );


    // --------------------------------------------------------
    // CRITICAL FIX
    // --------------------------------------------------------
    //
    // Loan Purpose remains a STRING.
    //
    // It is NOT passed to to_float().
    //
    // --------------------------------------------------------

    formData.append(
        "loan_purpose",
        valueOf("loan_purpose")
    );


    formData.append(
        "property_value",
        valueOf(
            "property_value"
        )
    );


    selectedFiles.forEach(
        function(file) {

            formData.append(
                "uploaded_files",
                file,
                file.name
            );

        }
    );


    try {

        processingText.textContent =
            "Creating secure loan processing session...";


        const response =
            await fetch(
                "/api/process",
                {
                    method: "POST",
                    body: formData
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "Unable to start processing"
            );

        }


        currentJobId =
            data.job_id;


        showToast(
            "AI loan processing started"
        );


        processingOverlay.classList.remove(
            "show"
        );


        document.getElementById(
            "trackerStatus"
        ).textContent =
            "PROCESSING";


        document.getElementById(
            "trackerMessage"
        ).textContent =
            "AI agents are analyzing the application";


        document.getElementById(
            "trackerSection"
        );


        startPolling();


        document.getElementById(
            "resultSection"
        ).scrollIntoView({
            behavior: "smooth"
        });

    }

    catch (error) {

        processingOverlay.classList.remove(
            "show"
        );

        processBtn.disabled = false;

        showToast(
            error.message ||
            "Unable to process application"
        );

    }

}


// ============================================================
// POLLING
// ============================================================

function startPolling() {

    if (pollingTimer) {

        clearInterval(
            pollingTimer
        );

    }


    pollStatus();


    pollingTimer =
        setInterval(
            pollStatus,
            900
        );

}


// ============================================================
// POLL STATUS
// ============================================================

async function pollStatus() {

    if (!currentJobId) {
        return;
    }


    try {

        const response =
            await fetch(
                "/api/status/" +
                currentJobId
            );


        const data =
            await response.json();


        if (!response.ok) {
            throw new Error(
                data.message ||
                "Status error"
            );
        }


        updateTracker(data);


        if (
            data.status === "completed"
        ) {

            clearInterval(
                pollingTimer
            );

            pollingTimer = null;

            await loadResult();

        }


        if (
            data.status === "error"
        ) {

            clearInterval(
                pollingTimer
            );

            pollingTimer = null;

            processBtn.disabled = false;

            processingOverlay.classList.remove(
                "show"
            );

            showToast(
                data.error ||
                "Loan processing failed"
            );

        }

    }

    catch (error) {

        console.error(
            "Polling error:",
            error
        );

    }

}


// ============================================================
// UPDATE TRACKER
// ============================================================

function updateTracker(data) {

    const progress =
        Number(
            data.progress || 0
        );


    document.getElementById(
        "progressFill"
    ).style.width =
        progress + "%";


    document.getElementById(
        "progressCount"
    ).textContent =
        data.completed_agents || 0;


    document.getElementById(
        "currentCount"
    ).textContent =
        (
            data.completed_agents || 0
        ) + " / 11";


    document.getElementById(
        "trackerMessage"
    ).textContent =
        data.message ||
        "Processing application";


    let statusText = "PROCESSING";


    if (
        data.status === "queued"
    ) {

        statusText = "QUEUED";

    }

    else if (
        data.status === "completed"
    ) {

        statusText = "COMPLETE";

    }

    else if (
        data.status === "error"
    ) {

        statusText = "ERROR";

    }


    document.getElementById(
        "trackerStatus"
    ).textContent =
        statusText;


    let currentName =
        "Waiting to start";


    if (
        data.active_agent &&
        data.active_agent >= 1 &&
        data.active_agent <= 11
    ) {

        const agent =
            AGENT_DATA[
                data.active_agent - 1
            ];

        if (agent) {

            currentName =
                agent.name;

        }

    }


    if (
        data.status === "completed"
    ) {

        currentName =
            "All AI agents completed";

    }


    document.getElementById(
        "currentAgent"
    ).textContent =
        currentName;


    updateAgents(
        data.agents || []
    );

}


// ============================================================
// LOAD RESULT
// ============================================================

async function loadResult() {

    try {

        const response =
            await fetch(
                "/api/result/" +
                currentJobId
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "Unable to load result"
            );

        }


        renderResult(data);


        processBtn.disabled = false;

        processingOverlay.classList.remove(
            "show"
        );


        showToast(
            "Loan application processing completed"
        );


        document.getElementById(
            "resultSection"
        ).style.display =
            "block";


        setTimeout(
            function() {

                document.getElementById(
                    "resultSection"
                ).scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });

            },
            250
        );

    }

    catch (error) {

        processBtn.disabled = false;

        showToast(
            error.message ||
            "Unable to load result"
        );

    }

}


// ============================================================
// FIND VALUE RECURSIVELY
// ============================================================

function findValue(
    object,
    keys
) {

    if (
        object === null ||
        object === undefined
    ) {
        return null;
    }


    if (
        typeof object !== "object"
    ) {
        return null;
    }


    for (
        const key of keys
    ) {

        if (
            Object.prototype.hasOwnProperty.call(
                object,
                key
            )
        ) {

            const value =
                object[key];

            if (
                value !== null &&
                value !== undefined &&
                String(value).trim() !== ""
            ) {

                return value;

            }

        }

    }


    for (
        const key of Object.keys(object)
    ) {

        const result =
            findValue(
                object[key],
                keys
            );

        if (
            result !== null &&
            result !== undefined
        ) {

            return result;

        }

    }


    return null;

}


// ============================================================
// RENDER RESULT
// ============================================================

function renderResult(data) {

    const result =
        data.result || {};

    const loanState =
        data.loan_state || {};


    const combined = {

        result: result,

        loan_state: loanState

    };


    let decision =
        findValue(
            combined,
            [
                "finalDecision",
                "final_decision",
                "decision",
                "decision_status",
                "finalDecisionStatus",
                "recommendation"
            ]
        );


    if (!decision) {

        decision =
            "PROCESSED";

    }


    const decisionText =
        String(
            decision
        );


    const upper =
        decisionText.toUpperCase();


    const badge =
        document.getElementById(
            "decisionBadge"
        );


    badge.classList.remove(
        "decision-approved",
        "decision-rejected",
        "decision-review"
    );


    if (
        upper.includes("APPROV")
    ) {

        badge.classList.add(
            "decision-approved"
        );

        badge.textContent =
            "✓ APPROVED";

    }

    else if (
        upper.includes("REJECT")
    ) {

        badge.classList.add(
            "decision-rejected"
        );

        badge.textContent =
            "× REJECTED";

    }

    else {

        badge.classList.add(
            "decision-review"
        );

        badge.textContent =
            "! HUMAN REVIEW";

    }


    const applicationId =
        findValue(
            combined,
            [
                "applicationId",
                "application_id",
                "loanApplicationId",
                "loan_id"
            ]
        ) ||
        "Loan Application";


    const applicant =
        findValue(
            combined,
            [
                "applicantName",
                "applicant_name",
                "full_name",
                "fullName"
            ]
        ) ||
        valueOf("full_name") ||
        "Applicant";


    document.getElementById(
        "resultApplicationId"
    ).textContent =
        applicationId;


    document.getElementById(
        "resultApplicant"
    ).textContent =
        applicant;


    document.getElementById(
        "resultDecision"
    ).textContent =
        decisionText;


    document.getElementById(
        "resultStatus"
    ).textContent =
        "Completed";


    const technicalData = {

        result: result,

        loan_state: loanState,

        processing_status:
            data.processing_status,

        pipeline_progress:
            data.pipeline_progress

    };


    document.getElementById(
        "jsonOutput"
    ).textContent =
        JSON.stringify(
            technicalData,
            null,
            2
        );


    if (
        data.pdf_available
    ) {

        const pdfUrl =
            "/api/pdf/" +
            currentJobId;

        const downloadUrl =
            "/api/download/" +
            currentJobId;


        const frame =
            document.getElementById(
                "pdfFrame"
            );

        frame.src =
            pdfUrl;

        frame.style.display =
            "block";


        const download =
            document.getElementById(
                "downloadBtn"
            );

        download.href =
            downloadUrl;

        download.style.display =
            "inline-flex";

    }

}


// ============================================================
// INITIAL SCROLL EFFECT
// ============================================================

window.addEventListener(
    "scroll",
    function() {

        const y =
            window.scrollY;

        const grid =
            document.querySelector(
                ".grid"
            );

        if (grid) {

            grid.style.transform =
                "perspective(700px) " +
                "rotateX(58deg) " +
                "translateY(" +
                (18 + y * .015) +
                "%)";

        }

    },
    {
        passive: true
    }
);


// ============================================================
// CINEMATIC VISUAL EFFECTS — VISUAL ONLY
// ============================================================

(function initCinematicEffects() {

    const cursor = document.getElementById("cinematicCursor");
    const particles = document.getElementById("cinematicParticles");
    const flash = document.getElementById("cinematicFlash");
    const house = document.querySelector(".house");
    const door = house ? house.querySelector(".door") : null;

    if (!cursor || !particles) return;

    /* Background particles remain present, but cursor bubbles now
       visually match their size, glow and movement. */
    for (let i = 0; i < 34; i++) {
        const p = document.createElement("span");
        p.className = "cinematic-particle";
        p.style.left = (Math.random() * 100) + "%";
        p.style.top = (100 + Math.random() * 20) + "%";
        p.style.animationDuration = (7 + Math.random() * 13) + "s";
        p.style.animationDelay = (-Math.random() * 14) + "s";
        p.style.setProperty("--drift", ((Math.random() - .5) * 110) + "px");
        p.style.opacity = (.18 + Math.random() * .55).toFixed(2);
        particles.appendChild(p);
    }

    let targetX = window.innerWidth / 2;
    let targetY = window.innerHeight / 2;
    let currentX = targetX;
    let currentY = targetY;
    let lastBubbleX = targetX;
    let lastBubbleY = targetY;
    let lastBubbleTime = 0;

    function createCursorBubble(x, y) {
        const bubble = document.createElement("span");
        bubble.className = "cinematic-cursor-bubble";

        const size = 3 + Math.random() * 7;
        const life = 650 + Math.random() * 650;
        const driftX = (Math.random() - .5) * 34;
        const driftY = -10 - Math.random() * 34;

        bubble.style.left = x + "px";
        bubble.style.top = y + "px";
        bubble.style.setProperty("--bubble-size", size + "px");
        bubble.style.setProperty("--bubble-life", life + "ms");
        bubble.style.setProperty("--bubble-drift-x", driftX + "px");
        bubble.style.setProperty("--bubble-drift-y", driftY + "px");

        document.body.appendChild(bubble);
        window.setTimeout(() => bubble.remove(), life + 80);
    }

    window.addEventListener("pointermove", function(event) {
        targetX = event.clientX;
        targetY = event.clientY;

        document.documentElement.style.setProperty("--mx", targetX + "px");
        document.documentElement.style.setProperty("--my", targetY + "px");

        const interactive = event.target.closest("button, input, select, textarea, .upload-box, a, .agent, .hero-stat, .new-btn");
        cursor.classList.toggle("hover", !!interactive);

        const now = performance.now();
        const distance = Math.hypot(targetX - lastBubbleX, targetY - lastBubbleY);

        /* Small bubbles appear only while the pointer is moving,
           creating a smooth particle trail instead of a large cursor ring. */
        if (distance > 7 && now - lastBubbleTime > 24) {
            const count = distance > 35 ? 2 : 1;
            for (let i = 0; i < count; i++) {
                const t = (i + 1) / (count + 1);
                createCursorBubble(
                    lastBubbleX + (targetX - lastBubbleX) * t,
                    lastBubbleY + (targetY - lastBubbleY) * t
                );
            }
            lastBubbleX = targetX;
            lastBubbleY = targetY;
            lastBubbleTime = now;
        }
    }, { passive: true });

    function animateCursor() {
        currentX += (targetX - currentX) * .18;
        currentY += (targetY - currentY) * .18;
        cursor.style.left = currentX + "px";
        cursor.style.top = currentY + "px";
        cursor.style.transform = "translate3d(-50%,-50%,0)";
        requestAnimationFrame(animateCursor);
    }
    animateCursor();

    /* Subtle cinematic parallax for the hero house only. */
    window.addEventListener("pointermove", function(event) {
        if (!house || window.innerWidth < 700) return;
        const x = (event.clientX / window.innerWidth - .5);
        const y = (event.clientY / window.innerHeight - .5);
        if (!house.classList.contains("door-hover")) {
            house.style.transform = `rotate(${(-3 + x * 3).toFixed(2)}deg) rotateY(${(x * 7).toFixed(2)}deg) rotateX(${(y * -5).toFixed(2)}deg)`;
        }
    }, { passive: true });

    /* Door interaction: a soft glowing beacon appears as the pointer approaches;
       the door opens only when the pointer actually reaches the door. */
    if (door && house) {
        let doorApproachActive = false;

        window.addEventListener("pointermove", function(event) {
            if (!door) return;

            const rect = (house.querySelector(".door-hit-area") || door).getBoundingClientRect();
            const doorX = rect.left + rect.width / 2;
            const doorY = rect.top + rect.height / 2;
            const dx = event.clientX - doorX;
            const dy = event.clientY - doorY;
            const distance = Math.sqrt(dx * dx + dy * dy);
            const nearDoor = distance < 125;

            if (nearDoor && !doorApproachActive) {
                house.classList.add("door-approach");
                doorApproachActive = true;
            } else if (!nearDoor && doorApproachActive && !house.classList.contains("door-hover")) {
                house.classList.remove("door-approach");
                doorApproachActive = false;
            }
        }, { passive: true });

        const doorHitArea = house.querySelector(".door-hit-area") || door;

        // The hit area never rotates. Only the visible door swings, so the
        // pointer can stay over the doorway while the door remains open.
        doorHitArea.addEventListener("mouseenter", function() {
            house.classList.remove("door-approach");
            doorApproachActive = false;
            house.classList.add("door-hover");
        });

        doorHitArea.addEventListener("mouseleave", function() {
            house.classList.remove("door-hover");
        });

        doorHitArea.style.cursor = "pointer";
    }

    /* Keep the existing Enter Application behavior visual-only.
       The house door is NOT opened by this button.
       It opens ONLY while the pointer is over the door. */
    if (typeof enterBtn !== "undefined" && enterBtn) {
        enterBtn.addEventListener("click", function() {
            if (flash) {
                flash.classList.remove("active");
                void flash.offsetWidth;
                flash.classList.add("active");
            }
            startScreen.classList.add("cinematic-exit");
        }, { passive: true });
    }

})();


</script>

</body>

</html>
"""


# ============================================================
# PROCESS API
# ============================================================

@loan_web_app.post("/api/process")
async def process_application_api(

    full_name: str = Form(...),
    date_of_birth: str = Form(...),
    pan: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(...),
    address: str = Form(...),

    employer: str = Form(...),

    years_of_experience: str = Form("0"),
    current_employment_years: str = Form("0"),

    gross_monthly_income: str = Form("0"),
    net_monthly_income: str = Form("0"),
    existing_monthly_emi: str = Form("0"),

    requested_loan_amount: str = Form("0"),

    loan_tenure_years: str = Form("20"),

    interest_rate: str = Form("8.5"),

    loan_purpose: str = Form("Property Purchase"),

    property_value: str = Form("0"),

    uploaded_files: Optional[
        List[UploadFile]
    ] = File(None)

):

    try:

        # ====================================================
        # BASIC VALIDATION
        # ====================================================

        required_fields = {
            "Full Name": full_name,
            "Date of Birth": date_of_birth,
            "PAN Number": pan,
            "Mobile Number": mobile,
            "Email": email,
            "Address": address,
            "Employer": employer,
            "Loan Purpose": loan_purpose
        }


        missing = [
            name
            for name, value
            in required_fields.items()
            if not str(value).strip()
        ]


        if missing:

            return JSONResponse(
                status_code=400,
                content={
                    "status": "ERROR",
                    "message":
                        "Missing required fields: "
                        + ", ".join(missing)
                }
            )


        # ====================================================
        # NUMERIC FIELDS
        # ====================================================
        #
        # CRITICAL:
        # loan_purpose is intentionally NOT here.
        #
        # ====================================================

        years_of_experience_num = to_float(
            years_of_experience,
            "Years of Experience"
        )

        current_employment_years_num = to_float(
            current_employment_years,
            "Current Employment Years"
        )

        gross_income_num = to_float(
            gross_monthly_income,
            "Gross Monthly Income"
        )

        net_income_num = to_float(
            net_monthly_income,
            "Net Monthly Income"
        )

        existing_emi_num = to_float(
            existing_monthly_emi,
            "Existing Monthly EMI"
        )

        requested_amount_num = to_float(
            requested_loan_amount,
            "Requested Loan Amount"
        )

        tenure_num = to_int(
            loan_tenure_years,
            "Loan Tenure"
        )

        interest_rate_num = to_float(
            interest_rate,
            "Interest Rate"
        )

        property_value_num = to_float(
            property_value,
            "Property Value"
        )


        # ====================================================
        # CREATE JOB
        # ====================================================

        job_id = create_job()


        # ====================================================
        # SAVE UPLOADED DOCUMENTS
        # ====================================================

        job_upload_dir = (
            UPLOAD_DIR / job_id
        )

        job_upload_dir.mkdir(
            parents=True,
            exist_ok=True
        )


        saved_files = []


        if uploaded_files:

            for uploaded_file in uploaded_files:

                if not uploaded_file:
                    continue

                original_name = (
                    uploaded_file.filename
                    or ""
                ).strip()

                if not original_name:
                    continue


                safe_filename = Path(
                    original_name
                ).name


                if not safe_filename.lower().endswith(
                    ".pdf"
                ):

                    continue


                destination_file = (
                    job_upload_dir /
                    safe_filename
                )


                contents = await uploaded_file.read()


                with open(
                    destination_file,
                    "wb"
                ) as file_handle:

                    file_handle.write(
                        contents
                    )


                saved_files.append(
                    str(destination_file)
                )


        # ====================================================
        # IMPORTANT BACKEND ARGUMENT ORDER
        # ====================================================
        #
        # 1  full_name
        # 2  date_of_birth
        # 3  pan
        # 4  mobile
        # 5  email
        # 6  address
        # 7  employer
        # 8  years_of_experience
        # 9  current_employment_years
        # 10 gross_monthly_income
        # 11 net_monthly_income
        # 12 existing_monthly_emi
        # 13 requested_loan_amount
        # 14 loan_tenure_years
        # 15 interest_rate
        # 16 loan_purpose
        # 17 property_value
        # 18 uploaded_files
        #
        # ====================================================

        application_args = [

            full_name,

            date_of_birth,

            pan,

            mobile,

            email,

            address,

            employer,

            years_of_experience_num,

            current_employment_years_num,

            gross_income_num,

            net_income_num,

            existing_emi_num,

            requested_amount_num,

            tenure_num,

            interest_rate_num,

            loan_purpose,

            property_value_num,

            saved_files

        ]


        # ====================================================
        # SAVE INPUT SNAPSHOT FOR DEBUGGING / TRACEABILITY
        # ====================================================

        with JOBS_LOCK:
            JOBS[job_id]["input_snapshot"] = {
                "full_name": full_name,
                "date_of_birth": date_of_birth,
                "pan": pan,
                "mobile": mobile,
                "email": email,
                "address": address,
                "employer": employer,
                "years_of_experience": years_of_experience_num,
                "current_employment_years": current_employment_years_num,
                "gross_monthly_income": gross_income_num,
                "net_monthly_income": net_income_num,
                "existing_monthly_emi": existing_emi_num,
                "requested_loan_amount": requested_amount_num,
                "loan_tenure_years": tenure_num,
                "interest_rate": interest_rate_num,
                "loan_purpose": loan_purpose,
                "property_value": property_value_num,
                "uploaded_files": saved_files
            }


        # ====================================================
        # START BACKGROUND PROCESS
        # ====================================================

        worker = threading.Thread(
            target=process_loan_job,
            args=(
                job_id,
                application_args
            ),
            daemon=True
        )

        worker.start()


        return {
            "status": "STARTED",
            "job_id": job_id,
            "message":
                "Loan application processing started"
        }


    except ValueError as exc:

        return JSONResponse(
            status_code=400,
            content={
                "status": "ERROR",
                "message": str(exc)
            }
        )


    except Exception as exc:

        print(
            "API ERROR:",
            repr(exc)
        )

        return JSONResponse(
            status_code=500,
            content={
                "status": "ERROR",
                "message": str(exc)
            }
        )


# ============================================================
# STATUS API
# ============================================================

@loan_web_app.get(
    "/api/status/{job_id}"
)
async def get_status(job_id: str):

    with JOBS_LOCK:

        job = JOBS.get(job_id)

        if job is None:

            return JSONResponse(
                status_code=404,
                content={
                    "status": "ERROR",
                    "message": "Job not found"
                }
            )


        return {
            "status": job["status"],
            "message": job["message"],
            "progress": job["progress"],
            "active_agent": job["active_agent"],
            "completed_agents": job[
                "completed_agents"
            ],
            "agents": job["agents"],
            "error": job["error"]
        }


# ============================================================
# RESULT API
# ============================================================

@loan_web_app.get(
    "/api/result/{job_id}"
)
async def get_result(job_id: str):

    with JOBS_LOCK:

        job = JOBS.get(job_id)

        if job is None:

            return JSONResponse(
                status_code=404,
                content={
                    "status": "ERROR",
                    "message": "Job not found"
                }
            )


        if job["status"] == "error":

            return JSONResponse(
                status_code=500,
                content={
                    "status": "ERROR",
                    "message":
                        job["error"]
                        or "Processing failed"
                }
            )


        return {
            "status": job["status"],
            "result": job["result"],
            "loan_state": job["loan_state"],
            "processing_status":
                job["processing_status"],
            "pipeline_progress":
                job["pipeline_progress"],
            "report_preview":
                job["report_preview"],
            "pdf_available":
                bool(job["pdf_path"])
        }


# ============================================================
# PDF VIEW
# ============================================================

@loan_web_app.get(
    "/api/pdf/{job_id}"
)
async def view_pdf(job_id: str):

    with JOBS_LOCK:

        job = JOBS.get(job_id)

        if job is None:

            return JSONResponse(
                status_code=404,
                content={
                    "status": "ERROR",
                    "message": "Job not found"
                }
            )


        pdf_path = job.get(
            "pdf_path"
        )


    if not pdf_path:

        return JSONResponse(
            status_code=404,
            content={
                "status": "ERROR",
                "message":
                    "PDF is not available yet"
            }
        )


    path = Path(pdf_path)


    if not path.exists():

        return JSONResponse(
            status_code=404,
            content={
                "status": "ERROR",
                "message":
                    "PDF file could not be found"
            }
        )


    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name
    )


# ============================================================
# PDF DOWNLOAD
# ============================================================

@loan_web_app.get(
    "/api/download/{job_id}"
)
async def download_pdf(job_id: str):

    with JOBS_LOCK:

        job = JOBS.get(job_id)

        if job is None:

            return JSONResponse(
                status_code=404,
                content={
                    "status": "ERROR",
                    "message": "Job not found"
                }
            )


        pdf_path = job.get(
            "pdf_path"
        )


    if not pdf_path:

        return JSONResponse(
            status_code=404,
            content={
                "status": "ERROR",
                "message":
                    "PDF is not available yet"
            }
        )


    path = Path(pdf_path)


    if not path.exists():

        return JSONResponse(
            status_code=404,
            content={
                "status": "ERROR",
                "message":
                    "PDF file could not be found"
            }
        )


    return FileResponse(
        path,
        media_type="application/pdf",
        filename=(
            "GenAI_Mortgage_Loan_Report.pdf"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="GenAI_Mortgage_Loan_Report.pdf"'
        }
    )


# ============================================================
# MAIN PAGE
# ============================================================

@loan_web_app.get(
    "/",
    response_class=HTMLResponse
)
async def home():

    return HTMLResponse(
        content=PAGE
    )


# ============================================================

# MANAGER DASHBOARD — PORTFOLIO / BULK EXCEL PROCESSING
# ============================================================
# IMPORTANT:
# This section ONLY adds the Manager workflow.
# The Individual Application workflow above is intentionally untouched.
# Manager processing uses structured Excel data directly and therefore
# does NOT send an empty document list through the Individual document gate.
# ============================================================

import pandas as pd
import math
import re
import html
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from reportlab.lib import colors as pdf_colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

MANAGER_BATCHES = {}
MANAGER_LOCK = threading.Lock()
MANAGER_MAX_WORKERS = max(1, int(os.getenv("MANAGER_MAX_WORKERS", "5")))

# Manager-only portfolio triage thresholds. These are NOT the Individual
# workflow policy and are presented as configurable demo screening bands.
MANAGER_POLICY = {
    "minimum_age": 21,
    "maximum_age_at_maturity": 65,
    "minimum_net_income": 25000,
    "maximum_ltv": 80.0,
    "human_review_ltv": 75.0,
    "maximum_foir": 75.0,
    "human_review_foir": 60.0,
    "minimum_loan": 500000,
    "maximum_loan": 100000000,
    "minimum_employment_years": 2,
    "default_interest_rate": 8.5,
    "default_tenure": 20,
}

MANAGER_ALIASES = {
    "application_id": ["Application ID", "ApplicationID", "App ID", "Loan Application ID"],
    "full_name": ["Full Name", "Name", "Applicant Name", "Applicant"],
    "date_of_birth": ["Date of Birth", "DOB", "Birth Date"],
    "pan": ["PAN Number", "PAN", "PAN No"],
    "mobile": ["Mobile Number", "Mobile", "Phone", "Phone Number"],
    "email": ["Email", "Email Address"],
    "address": ["Address", "Residential Address", "Complete Residential Address"],
    "employer": ["Employer", "Company", "Company / Employer", "Company/Employer"],
    "years_of_experience": ["Years of Experience", "Experience", "Total Experience"],
    "current_employment_years": ["Current Employment Years", "Current Employment", "Current Job Years"],
    "gross_monthly_income": ["Gross Monthly Income", "Gross Monthly Income (INR)", "Gross Income", "Monthly Gross Income"],
    "net_monthly_income": ["Net Monthly Income", "Net Monthly Income (INR)", "Net Income", "Monthly Net Income"],
    "existing_monthly_emi": ["Existing Monthly EMI", "Existing Monthly EMI (INR)", "Existing EMI", "Monthly EMI"],
    "requested_loan_amount": ["Requested Loan Amount", "Requested Loan Amount (INR)", "Loan Amount", "Loan Amount (INR)"],
    "loan_tenure_years": ["Loan Tenure", "Loan Tenure Years", "Tenure", "Loan Tenure (Years)"],
    "interest_rate": ["Interest Rate", "Interest Rate (%)", "ROI", "Rate"],
    "loan_purpose": ["Loan Purpose", "Purpose"],
    "property_value": ["Property Value", "Property Value (INR)", "Property Price", "Property Cost"],
    "documents_status": ["Documents Status", "Document Status", "Documents", "KYC Status"],
    "missing_documents": ["Missing Documents", "Missing Document", "Documents Missing"],
}


def _mnorm(x):
    return re.sub(r"[^a-z0-9]+", "", str(x).strip().lower())


def _mval(row, field):
    cols = {_mnorm(k): v for k, v in row.items()}
    for alias in MANAGER_ALIASES.get(field, []):
        key = _mnorm(alias)
        if key in cols:
            value = cols[key]
            if pd.isna(value):
                return ""
            return str(value).strip()
    return ""


def _mid(row, i):
    return _mval(row, "application_id") or f"APP-{datetime.now().strftime('%Y%m%d')}-{i+1:04d}"


def _mfloat(value, default=0.0):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    try:
        return float(str(value).replace(",", "").replace("₹", "").replace("%", "").strip())
    except Exception:
        return default


def _mdate_age(value):
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            dob = datetime.strptime(text, fmt)
            today = datetime.today()
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except Exception:
            pass
    return None


def _calc_emi(principal, annual_rate, tenure_years):
    principal = float(principal or 0)
    rate = float(annual_rate or 0) / 12 / 100
    months = max(1, int(float(tenure_years or 1)) * 12)
    if principal <= 0:
        return 0.0
    if rate == 0:
        return round(principal / months, 2)
    return round(principal * rate * (1 + rate) ** months / ((1 + rate) ** months - 1), 2)


def _money(v):
    return f"₹{float(v or 0):,.0f}"


def _manager_document_review(row):
    status = _mval(row, "documents_status").lower()
    missing = _mval(row, "missing_documents")
    if missing:
        return [f"Missing documents: {missing}"]
    if any(x in status for x in ["missing", "incomplete", "pending", "not available", "required"]):
        return [f"Document status: {_mval(row, 'documents_status')}"]
    return []


def _manager_assess(row, index):
    '''Manager-only structured portfolio assessment. Individual workflow is untouched.'''
    started = time.time()
    aid = _mid(row, index)
    name = _mval(row, "full_name") or "Not Available"
    review_flags, decline_flags, data_flags = [], [], []

    dob = _mval(row, "date_of_birth")
    age = _mdate_age(dob)
    net_income = _mfloat(_mval(row, "net_monthly_income"))
    existing_emi = _mfloat(_mval(row, "existing_monthly_emi"))
    loan = _mfloat(_mval(row, "requested_loan_amount"))
    property_value = _mfloat(_mval(row, "property_value"))
    tenure = _mfloat(_mval(row, "loan_tenure_years"), MANAGER_POLICY["default_tenure"])
    rate = _mfloat(_mval(row, "interest_rate"), MANAGER_POLICY["default_interest_rate"])
    employment = _mfloat(_mval(row, "current_employment_years"))

    # STRICT MANAGER DATA GATE
    # Any mandatory applicant / loan field that is blank is NEVER auto-approved.
    raw_fields = {
        "Full Name": _mval(row, "full_name"),
        "Date of Birth": dob,
        "PAN Number": _mval(row, "pan"),
        "Mobile Number": _mval(row, "mobile"),
        "Email": _mval(row, "email"),
        "Address": _mval(row, "address"),
        "Employer": _mval(row, "employer"),
        "Years of Experience": _mval(row, "years_of_experience"),
        "Current Employment Years": _mval(row, "current_employment_years"),
        "Gross Monthly Income": _mval(row, "gross_monthly_income"),
        "Net Monthly Income": _mval(row, "net_monthly_income"),
        "Existing Monthly EMI": _mval(row, "existing_monthly_emi"),
        "Loan Amount": _mval(row, "requested_loan_amount"),
        "Loan Tenure": _mval(row, "loan_tenure_years"),
        "Interest Rate": _mval(row, "interest_rate"),
        "Loan Purpose": _mval(row, "loan_purpose"),
        "Property Value": _mval(row, "property_value"),
        "Documents Status": _mval(row, "documents_status"),
    }
    missing = [k for k, v in raw_fields.items() if not str(v or "").strip()]
    if missing:
        data_flags.append("Missing mandatory data: " + ", ".join(missing))

    # Basic format validation. Invalid values also route to HUMAN REVIEW.
    pan = raw_fields["PAN Number"].upper().replace(" ", "")
    mobile = re.sub(r"\D", "", raw_fields["Mobile Number"])
    email = raw_fields["Email"]
    if pan and not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan):
        data_flags.append("PAN number format could not be validated")
    if mobile and len(mobile) != 10:
        data_flags.append("Mobile number must contain 10 digits")
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        data_flags.append("Email format could not be validated")

    gross_income = _mfloat(_mval(row, "gross_monthly_income"))
    experience = _mfloat(_mval(row, "years_of_experience"), -1)
    if raw_fields["Gross Monthly Income"] and gross_income <= 0:
        data_flags.append("Gross monthly income is not valid")
    if raw_fields["Years of Experience"] and experience < 0:
        data_flags.append("Years of experience is not valid")
    if raw_fields["Loan Tenure"] and tenure <= 0:
        data_flags.append("Loan tenure must be greater than zero")
    if raw_fields["Interest Rate"] and rate <= 0:
        data_flags.append("Interest rate must be greater than zero")

    if age is None:
        data_flags.append("Date of birth could not be validated")
    else:
        if age < MANAGER_POLICY["minimum_age"]:
            decline_flags.append(f"Applicant age {age} is below the minimum of {MANAGER_POLICY['minimum_age']}")
        if age + int(tenure or 0) > MANAGER_POLICY["maximum_age_at_maturity"]:
            decline_flags.append(f"Age at loan maturity would exceed {MANAGER_POLICY['maximum_age_at_maturity']} years")

    if net_income <= 0:
        data_flags.append("Net monthly income is not valid")
    elif net_income < MANAGER_POLICY["minimum_net_income"]:
        decline_flags.append(f"Net monthly income {_money(net_income)} is below the portfolio minimum of {_money(MANAGER_POLICY['minimum_net_income'])}")

    if loan < MANAGER_POLICY["minimum_loan"] or loan > MANAGER_POLICY["maximum_loan"]:
        decline_flags.append(f"Requested loan {_money(loan)} is outside the configured loan range")

    if property_value <= 0:
        data_flags.append("Property value is not valid")
        ltv = None
    else:
        ltv = round((loan / property_value) * 100, 2) if loan > 0 else 0.0
        if ltv > MANAGER_POLICY["maximum_ltv"]:
            decline_flags.append(f"Loan-to-value is {ltv:.1f}%, above the {MANAGER_POLICY['maximum_ltv']:.0f}% ceiling")
        elif ltv > MANAGER_POLICY["human_review_ltv"]:
            review_flags.append(f"Loan-to-value is {ltv:.1f}%, requiring manual review")

    proposed_emi = _calc_emi(loan, rate, tenure) if loan > 0 else 0.0
    foir = round(((existing_emi + proposed_emi) / net_income) * 100, 2) if net_income > 0 else None
    if foir is not None:
        if foir > MANAGER_POLICY["maximum_foir"]:
            decline_flags.append(f"FOIR is {foir:.1f}%, above the {MANAGER_POLICY['maximum_foir']:.0f}% hard-decline threshold")
        elif foir > MANAGER_POLICY["human_review_foir"]:
            review_flags.append(f"FOIR is {foir:.1f}%, above the {MANAGER_POLICY['human_review_foir']:.0f}% review threshold")

    if employment < MANAGER_POLICY["minimum_employment_years"]:
        review_flags.append(f"Current employment is {employment:g} years; manual stability review recommended")

    review_flags.extend(_manager_document_review(row))

    if data_flags:
        status = "HUMAN REVIEW"
        reasons = data_flags + review_flags
        summary = "Manual review required because the Excel record is missing or contains data that could not be validated."
    elif decline_flags:
        status = "DECLINED"
        reasons = decline_flags[:4]
        summary = "Portfolio screening identified one or more hard eligibility exceptions."
    elif review_flags:
        status = "HUMAN REVIEW"
        reasons = review_flags[:4]
        summary = "Financial metrics are not an automatic decline, but one or more review flags require manual assessment."
    else:
        # Final fail-safe: approval is possible only when the strict data gate,
        # hard eligibility checks and review checks are all clear.
        if data_flags or decline_flags or review_flags:
            status = "HUMAN REVIEW"
            reasons = (data_flags + review_flags)[:4] or ["Manual review required before approval"]
            summary = "Manual review required because one or more required applicant, document or risk checks were not fully satisfied."
        else:
            status = "APPROVED"
            reasons = [
                f"FOIR {foir:.1f}% is within the {MANAGER_POLICY['human_review_foir']:.0f}% automated approval band",
                f"LTV {ltv:.1f}% is within the {MANAGER_POLICY['human_review_ltv']:.0f}% automated approval band",
                f"Net monthly income {_money(net_income)} meets the minimum requirement",
            ]
            summary = "Portfolio screening passed the configured automated affordability, LTV, income and employment checks."

    return {
        "index": index, "application_id": aid, "applicant": name, "status": status,
        "reason": "; ".join(reasons) if reasons else "No specific exception identified.",
        "summary": summary, "age": age, "dob": dob,
        "pan": raw_fields["PAN Number"], "mobile": raw_fields["Mobile Number"],
        "email": raw_fields["Email"], "address": raw_fields["Address"],
        "employer": raw_fields["Employer"],
        "years_of_experience": experience if experience >= 0 else 0,
        "gross_income": round(gross_income, 2), "net_income": round(net_income, 2),
        "existing_emi": round(existing_emi, 2), "loan_amount": round(loan, 2),
        "property_value": round(property_value, 2), "proposed_emi": round(proposed_emi, 2),
        "foir": foir, "ltv": ltv, "employment_years": employment, "interest_rate": rate,
        "tenure": tenure, "loan_purpose": raw_fields["Loan Purpose"],
        "documents_status": raw_fields["Documents Status"],
        "missing_documents": _mval(row, "missing_documents"),
        "tenure": tenure, "processing_seconds": round(time.time() - started, 2), "error": None,
    }


def _one_manager(batch_id, index, row):
    with MANAGER_LOCK:
        MANAGER_BATCHES[batch_id]["rows"][index]["status"] = "PROCESSING"
    try:
        return _manager_assess(row, index)
    except Exception as exc:
        return {
            "index": index, "application_id": _mid(row, index),
            "applicant": _mval(row, "full_name") or "Not Available", "status": "HUMAN REVIEW",
            "reason": f"Processing exception: {exc}",
            "summary": "Automated portfolio assessment failed and requires manual review.",
            "processing_seconds": 0, "error": str(exc),
        }



# ------------------------------------------------------------
# PDF ENGINE — optimized consolidated + individual reports
# ------------------------------------------------------------

_MANAGER_FONT_READY = False

def _register_manager_fonts():
    global _MANAGER_FONT_READY
    if _MANAGER_FONT_READY:
        return
    regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(regular) and os.path.exists(bold):
        try:
            pdfmetrics.registerFont(TTFont("MortgageSans", regular))
            pdfmetrics.registerFont(TTFont("MortgageSansBold", bold))
            _MANAGER_FONT_READY = True
        except Exception:
            pass

def _manager_fonts():
    _register_manager_fonts()
    return ("MortgageSans", "MortgageSansBold") if _MANAGER_FONT_READY else ("Helvetica", "Helvetica-Bold")

def _pdf_escape(value):
    return html.escape(str(value if value is not None else ""))

def _status_color(status):
    status = str(status or "").upper()
    if status == "APPROVED":
        return pdf_colors.HexColor("#0f9f6e")
    if status == "DECLINED":
        return pdf_colors.HexColor("#dc4c63")
    if status == "HUMAN REVIEW":
        return pdf_colors.HexColor("#d49400")
    return pdf_colors.HexColor("#5b8def")

def _manager_pdf_header_footer(canvas, doc):
    regular, bold = _manager_fonts()
    canvas.saveState()
    width, height = landscape(A4)
    canvas.setFillColor(pdf_colors.HexColor("#071a2c"))
    canvas.rect(0, height - 8*mm, width, 8*mm, fill=1, stroke=0)
    canvas.setFillColor(pdf_colors.HexColor("#6fe0ff"))
    canvas.setFont(bold, 7.5)
    canvas.drawString(12*mm, height - 5.2*mm, "GEN AI MORTGAGE")
    canvas.setFillColor(pdf_colors.HexColor("#71869a"))
    canvas.setFont(regular, 6.5)
    canvas.drawRightString(width - 12*mm, 6*mm, f"Manager Portfolio • Page {doc.page}")
    canvas.restoreState()

def _manager_pdf_styles():
    regular, bold = _manager_fonts()
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("m_title", parent=styles["Title"], fontName=bold, fontSize=23, leading=27, textColor=pdf_colors.HexColor("#071a2c"), spaceAfter=3),
        "subtitle": ParagraphStyle("m_subtitle", parent=styles["BodyText"], fontName=regular, fontSize=8.5, leading=11, textColor=pdf_colors.HexColor("#66788a")),
        "section": ParagraphStyle("m_section", parent=styles["Heading2"], fontName=bold, fontSize=12.5, leading=15, textColor=pdf_colors.HexColor("#0b2944"), spaceBefore=6, spaceAfter=6),
        "body": ParagraphStyle("m_body", parent=styles["BodyText"], fontName=regular, fontSize=8.2, leading=11, textColor=pdf_colors.HexColor("#34495a")),
        "small": ParagraphStyle("m_small", parent=styles["BodyText"], fontName=regular, fontSize=7.1, leading=9.1, textColor=pdf_colors.HexColor("#34495a")),
        "small_bold": ParagraphStyle("m_small_bold", parent=styles["BodyText"], fontName=bold, fontSize=7.1, leading=9.1, textColor=pdf_colors.HexColor("#18344d")),
        "table_head": ParagraphStyle("m_table_head", parent=styles["BodyText"], fontName=bold, fontSize=6.7, leading=8, textColor=pdf_colors.white),
        "table": ParagraphStyle("m_table", parent=styles["BodyText"], fontName=regular, fontSize=6.6, leading=8.2, textColor=pdf_colors.HexColor("#24384a")),
        "table_bold": ParagraphStyle("m_table_bold", parent=styles["BodyText"], fontName=bold, fontSize=6.6, leading=8.2, textColor=pdf_colors.HexColor("#102a42")),
        "center_small": ParagraphStyle("m_center_small", parent=styles["BodyText"], fontName=regular, fontSize=7, leading=9, alignment=TA_CENTER, textColor=pdf_colors.HexColor("#52687b")),
    }

def _status_paragraph(status, styles):
    return Paragraph(
        f"<font color='{_status_color(status).hexval()}'><b>{_pdf_escape(status)}</b></font>",
        styles["small_bold"]
    )

def _build_manager_summary_pdf(rows, batch_id, path):
    styles = _manager_pdf_styles()
    approved = sum(r.get("status") == "APPROVED" for r in rows)
    declined = sum(r.get("status") == "DECLINED" for r in rows)
    review = sum(r.get("status") == "HUMAN REVIEW" for r in rows)

    doc = SimpleDocTemplate(
        str(path), pagesize=landscape(A4),
        rightMargin=11*mm, leftMargin=11*mm, topMargin=14*mm, bottomMargin=11*mm,
        title="Gen AI Mortgage — Manager Portfolio Report", author="Gen AI Mortgage"
    )
    styles = _manager_pdf_styles()
    story = [
        Paragraph("Manager Portfolio Assessment", styles["title"]),
        Paragraph(
            f"Batch <b>{_pdf_escape(batch_id)}</b> &nbsp; • &nbsp; Generated {datetime.now().strftime('%d %b %Y, %H:%M')}",
            styles["subtitle"]
        ),
        Spacer(1, 7)
    ]

    kpi = Table([
        [Paragraph("<b>TOTAL APPLICATIONS</b>", styles["table_head"]),
         Paragraph("<b>APPROVED</b>", styles["table_head"]),
         Paragraph("<b>DECLINED</b>", styles["table_head"]),
         Paragraph("<b>HUMAN REVIEW</b>", styles["table_head"])],
        [Paragraph(f"<font size='19'><b>{len(rows)}</b></font>", styles["center_small"]),
         Paragraph(f"<font size='19'><b>{approved}</b></font>", styles["center_small"]),
         Paragraph(f"<font size='19'><b>{declined}</b></font>", styles["center_small"]),
         Paragraph(f"<font size='19'><b>{review}</b></font>", styles["center_small"])]
    ], colWidths=[63*mm,51*mm,51*mm,55*mm], rowHeights=[9*mm,13*mm])
    kpi.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),pdf_colors.HexColor("#0b2944")),
        ("BACKGROUND",(0,1),(-1,1),pdf_colors.HexColor("#f4f7fa")),
        ("GRID",(0,0),(-1,-1),.35,pdf_colors.HexColor("#d6dee6")),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE")
    ]))
    story += [kpi, Spacer(1,8), Paragraph("Portfolio Results", styles["section"]),
              Paragraph("Compact manager view. Use the web dashboard Application ID links to open the full individual assessment PDF.", styles["body"]),
              Spacer(1,5)]

    data = [[Paragraph("APPLICATION ID", styles["table_head"]),
             Paragraph("APPLICANT", styles["table_head"]),
             Paragraph("STATUS", styles["table_head"]),
             Paragraph("FOIR", styles["table_head"]),
             Paragraph("LTV", styles["table_head"]),
             Paragraph("LOAN", styles["table_head"]),
             Paragraph("DECISION REASON", styles["table_head"])]]

    for r in rows:
        data.append([
            Paragraph(f"<b>{_pdf_escape(r.get('application_id'))}</b>", styles["table_bold"]),
            Paragraph(_pdf_escape(r.get("applicant")), styles["table"]),
            _status_paragraph(r.get("status"), styles),
            Paragraph(f"{r.get('foir')}%" if r.get("foir") is not None else "—", styles["table"]),
            Paragraph(f"{r.get('ltv')}%" if r.get("ltv") is not None else "—", styles["table"]),
            Paragraph(_money(r.get("loan_amount",0)), styles["table"]),
            Paragraph(_pdf_escape(r.get("reason")), styles["table"])
        ])

    rt = Table(data, colWidths=[29*mm,34*mm,31*mm,19*mm,19*mm,30*mm,107*mm], repeatRows=1, splitByRow=1)
    rules = [
        ("BACKGROUND",(0,0),(-1,0),pdf_colors.HexColor("#0b2944")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("GRID",(0,0),(-1,-1),.3,pdf_colors.HexColor("#d7e0e8")),
        ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)
    ]
    for i, r in enumerate(rows, 1):
        bg = "#f1fbf7" if r.get("status")=="APPROVED" else "#fff3f5" if r.get("status")=="DECLINED" else "#fff9ed"
        rules.append(("BACKGROUND",(0,i),(-1,i),pdf_colors.HexColor(bg)))
    rt.setStyle(TableStyle(rules))
    story += [rt, Spacer(1,7), HRFlowable(width="100%", thickness=.5, color=pdf_colors.HexColor("#d9e2e9")),
              Spacer(1,4), Paragraph("Assessment Method", styles["section"]),
              Paragraph(
                  "Manager-only portfolio screening uses structured Excel fields. It does not invoke the Individual Application document checklist. The demo uses affordability/FOIR, LTV, income, age, loan-range and employment checks. Human Review is used for missing/uncertain data and borderline cases. These thresholds are configurable demo triage rules and are not a lending policy.",
                  styles["body"]
              )]
    doc.build(story, onFirstPage=_manager_pdf_header_footer, onLaterPages=_manager_pdf_header_footer)

def _manager_pdf(batch_id):
    with MANAGER_LOCK:
        rows = sorted(list(MANAGER_BATCHES[batch_id].get("results", [])), key=lambda x:x.get("index",0))
    out_dir = BASE_DIR/"manager_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir/f"{batch_id}_manager_report.pdf"
    _build_manager_summary_pdf(rows, batch_id, path)
    return str(path)

def _build_manager_individual_pdf(row, result, batch_id, path):
    styles = _manager_pdf_styles()
    regular, bold = _manager_fonts()
    doc = SimpleDocTemplate(
        str(path), pagesize=A4, rightMargin=15*mm, leftMargin=15*mm,
        topMargin=16*mm, bottomMargin=15*mm,
        title=f"Mortgage Application Report — {result.get('application_id')}",
        author="Gen AI Mortgage"
    )

    def footer(canvas, doc_obj):
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(pdf_colors.HexColor("#071a2c"))
        canvas.rect(0,height-8*mm,width,8*mm,fill=1,stroke=0)
        canvas.setFillColor(pdf_colors.HexColor("#6fe0ff"))
        canvas.setFont(bold,7.5)
        canvas.drawString(15*mm,height-5.2*mm,"GEN AI MORTGAGE")
        canvas.setFillColor(pdf_colors.HexColor("#71869a"))
        canvas.setFont(regular,6.5)
        canvas.drawRightString(width-15*mm,7*mm,f"Application Report • Page {doc_obj.page}")
        canvas.restoreState()

    story = [
        Spacer(1,4),
        Paragraph("Mortgage Application Assessment", styles["title"]),
        Paragraph(
            f"Application ID <b>{_pdf_escape(result.get('application_id'))}</b> &nbsp; • &nbsp; Batch {_pdf_escape(batch_id)}",
            styles["subtitle"]
        ),
        Spacer(1,8)
    ]

    status = str(result.get("status") or "HUMAN REVIEW")
    decision = Table([[
        Paragraph("<b>DECISION</b>", styles["table_head"]),
        Paragraph(f"<font color='{_status_color(status).hexval()}'><b>{_pdf_escape(status)}</b></font>", styles["body"])
    ]], colWidths=[38*mm,130*mm])
    decision.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,0),pdf_colors.HexColor("#0b2944")),
        ("BACKGROUND",(1,0),(1,0),pdf_colors.HexColor("#f6f8fa")),
        ("GRID",(0,0),(-1,-1),.4,pdf_colors.HexColor("#d5dee7")),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)
    ]))
    story += [decision, Spacer(1,8), Paragraph("Decision Explanation", styles["section"]),
              Paragraph(_pdf_escape(result.get("reason")), styles["body"]),
              Spacer(1,4), Paragraph(_pdf_escape(result.get("summary")), styles["body"]), Spacer(1,9)]

    metrics = [
        [Paragraph("<b>NET INCOME</b>",styles["table_head"]),Paragraph("<b>EXISTING EMI</b>",styles["table_head"]),Paragraph("<b>PROPOSED EMI</b>",styles["table_head"]),Paragraph("<b>FOIR</b>",styles["table_head"])],
        [Paragraph(_money(result.get("net_income")),styles["body"]),Paragraph(_money(result.get("existing_emi")),styles["body"]),Paragraph(_money(result.get("proposed_emi")),styles["body"]),Paragraph(f"{result.get('foir')}%" if result.get("foir") is not None else "—",styles["body"])],
        [Paragraph("<b>LTV</b>",styles["table_head"]),Paragraph("<b>LOAN AMOUNT</b>",styles["table_head"]),Paragraph("<b>PROPERTY VALUE</b>",styles["table_head"]),Paragraph("<b>RATE / TENURE</b>",styles["table_head"])],
        [Paragraph(f"{result.get('ltv')}%" if result.get("ltv") is not None else "—",styles["body"]),Paragraph(_money(result.get("loan_amount")),styles["body"]),Paragraph(_money(result.get("property_value")),styles["body"]),Paragraph(f"{result.get('interest_rate')}% / {result.get('tenure')} years",styles["body"])]
    ]
    mt = Table(metrics,colWidths=[42*mm,42*mm,42*mm,42*mm])
    mt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),pdf_colors.HexColor("#0b2944")),
        ("BACKGROUND",(0,2),(-1,2),pdf_colors.HexColor("#0b2944")),
        ("BACKGROUND",(0,1),(-1,1),pdf_colors.HexColor("#f6f9fb")),
        ("BACKGROUND",(0,3),(-1,3),pdf_colors.HexColor("#f6f9fb")),
        ("GRID",(0,0),(-1,-1),.35,pdf_colors.HexColor("#d5dee7")),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)
    ]))
    story += [mt, Spacer(1,10)]

    def info_table(title, pairs):
        data = [[Paragraph(f"<b>{_pdf_escape(title)}</b>", styles["table_head"])]]
        for label,value in pairs:
            data.append([Paragraph(
                f"<b>{_pdf_escape(label)}</b><br/>{_pdf_escape(value if value not in [None,''] else 'Not provided')}",
                styles["small"]
            )])
        t = Table(data,colWidths=[168*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),pdf_colors.HexColor("#0b2944")),
            ("GRID",(0,0),(-1,-1),.35,pdf_colors.HexColor("#d5dee7")),
            ("BACKGROUND",(0,1),(-1,-1),pdf_colors.white),
            ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)
        ]))
        return t

    story += [
        info_table("Applicant Information",[
            ("Full Name",result.get("applicant")),
            ("Date of Birth / Age",f"{result.get('dob') or 'Not provided'} / {result.get('age') if result.get('age') is not None else 'Not validated'}"),
            ("PAN",result.get("pan")),("Mobile",result.get("mobile")),("Email",result.get("email")),("Address",result.get("address"))
        ]),
        Spacer(1,8),
        info_table("Employment & Loan Information",[
            ("Employer",result.get("employer")),
            ("Experience",f"{result.get('years_of_experience',0):g} years"),
            ("Current Employment",f"{result.get('employment_years',0):g} years"),
            ("Gross Monthly Income",_money(result.get("gross_income"))),
            ("Loan Purpose",result.get("loan_purpose")),
            ("Documents Status",result.get("documents_status")),
            ("Missing Documents",result.get("missing_documents"))
        ]),
        Spacer(1,8),
        Paragraph("Assessment Note",styles["section"]),
        Paragraph(
            "This individual report is generated from the Manager Portfolio Assessment workflow using the structured Excel record. It is a manager triage report and does not replace the Individual Application workflow, lender verification, or final underwriting.",
            styles["body"]
        )
    ]
    doc.build(story,onFirstPage=footer,onLaterPages=footer)

def _manager_individual_pdf(batch_id,index):
    with MANAGER_LOCK:
        batch=MANAGER_BATCHES.get(batch_id)
        if not batch:
            return None,None
        results=batch.get("results",[])
        records=batch.get("records",[])
        if index<0 or index>=len(results) or index>=len(records):
            return None,None
        result=results[index]
        record=records[index]

    out_dir=BASE_DIR/"manager_reports"/batch_id/"applications"
    out_dir.mkdir(parents=True,exist_ok=True)
    safe_id=re.sub(r"[^A-Za-z0-9._-]+","_",str(result.get("application_id") or f"application_{index+1}"))
    path=out_dir/f"{safe_id}_assessment.pdf"
    if not path.exists():
        _build_manager_individual_pdf(record,result,batch_id,path)
    return str(path),result.get("application_id")

# ------------------------------------------------------------
# MANAGER BATCH PROCESSING
# ------------------------------------------------------------

def _run_manager_batch(batch_id, df):
    records = df.to_dict(orient="records")
    total = len(records)

    with MANAGER_LOCK:
        MANAGER_BATCHES[batch_id].update(
            status="PROCESSING",
            total=total,
            records=records,
            rows=[
                {
                    "index": i,
                    "application_id": _mid(row, i),
                    "applicant": _mval(row, "full_name") or "Not Available",
                    "status": "QUEUED",
                    "reason": "",
                    "summary": "Waiting for assessment…",
                }
                for i, row in enumerate(records)
            ],
        )

    results = [None] * total

    try:
        with ThreadPoolExecutor(max_workers=min(MANAGER_MAX_WORKERS, total)) as executor:
            futures = {
                executor.submit(_one_manager, batch_id, i, row): i
                for i, row in enumerate(records)
            }
            completed = 0

            for future in as_completed(futures):
                i = futures[future]
                results[i] = future.result()
                completed += 1
                r = results[i]

                with MANAGER_LOCK:
                    MANAGER_BATCHES[batch_id]["rows"][i].update(
                        {
                            "application_id": r.get("application_id"),
                            "applicant": r.get("applicant"),
                            "status": r.get("status"),
                            "reason": r.get("reason"),
                            "summary": r.get("summary"),
                            "foir": r.get("foir"),
                            "ltv": r.get("ltv"),
                        }
                    )
                    MANAGER_BATCHES[batch_id].update(
                        completed=completed,
                        progress=int((completed / total) * 100),
                        message=f"Assessing {completed} of {total} applications",
                    )

        with MANAGER_LOCK:
            MANAGER_BATCHES[batch_id].update(
                results=results,
                status="REPORT_GENERATING",
                message="Generating optimized consolidated manager report",
            )

        report_path = _manager_pdf(batch_id)

        with MANAGER_LOCK:
            MANAGER_BATCHES[batch_id].update(
                status="COMPLETED",
                progress=100,
                completed=total,
                approved=sum(r.get("status") == "APPROVED" for r in results),
                declined=sum(r.get("status") == "DECLINED" for r in results),
                human_review=sum(r.get("status") == "HUMAN REVIEW" for r in results),
                manager_pdf=report_path,
                message="Portfolio assessment completed",
            )

    except Exception as exc:
        with MANAGER_LOCK:
            MANAGER_BATCHES[batch_id].update(
                status="ERROR",
                message=f"Manager processing failed: {exc}",
                error=str(exc),
            )



MANAGER_TEMPLATE_COLUMNS=["Application ID","Full Name","Date of Birth","PAN Number","Mobile Number","Email","Address","Employer","Years of Experience","Current Employment Years","Gross Monthly Income (INR)","Net Monthly Income (INR)","Existing Monthly EMI (INR)","Loan Amount (INR)","Loan Tenure (Years)","Interest Rate (%)","Loan Purpose","Property Value (INR)","Documents Status","Missing Documents"]


@loan_web_app.get("/manager", response_class=HTMLResponse)
async def manager_dashboard():
    return HTMLResponse(MANAGER_PAGE)


@loan_web_app.post("/api/manager/upload")
async def manager_upload(file: UploadFile = File(...)):
    try:
        filename=(file.filename or "").lower()
        if not filename.endswith((".xlsx",".xls")):
            return JSONResponse(status_code=400,content={"status":"ERROR","message":"Please upload an .xlsx or .xls Excel file."})

        raw=await file.read()
        import io
        df=pd.read_excel(io.BytesIO(raw)).dropna(how="all").reset_index(drop=True)

        if df.empty:
            return JSONResponse(status_code=400,content={"status":"ERROR","message":"The Excel file contains no applicant rows."})
        if len(df)>500:
            return JSONResponse(status_code=400,content={"status":"ERROR","message":"Maximum 500 applications per batch."})

        batch_id="BATCH-"+datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6].upper()

        with MANAGER_LOCK:
            MANAGER_BATCHES[batch_id]={
                "batch_id":batch_id,"status":"QUEUED","message":"Excel accepted",
                "progress":0,"total":len(df),"completed":0,"approved":0,
                "declined":0,"human_review":0,"rows":[],"results":[],"records":[],
                "manager_pdf":None,"error":None
            }

        threading.Thread(target=_run_manager_batch,args=(batch_id,df),daemon=True).start()

        return {
            "status":"SUCCESS","batch_id":batch_id,"total":len(df),
            "message":f"{len(df)} applications queued for portfolio assessment."
        }

    except Exception as exc:
        return JSONResponse(status_code=400,content={"status":"ERROR","message":f"Unable to read Excel file: {exc}"})


@loan_web_app.get("/api/manager/status/{batch_id}")
async def manager_status(batch_id:str):
    with MANAGER_LOCK:
        batch=MANAGER_BATCHES.get(batch_id)
    if not batch:
        return JSONResponse(status_code=404,content={"status":"ERROR","message":"Batch not found."})

    return {
        "status":batch["status"],"batch_id":batch_id,"message":batch.get("message"),
        "progress":batch.get("progress",0),"total":batch.get("total",0),
        "completed":batch.get("completed",0),"approved":batch.get("approved",0),
        "declined":batch.get("declined",0),"human_review":batch.get("human_review",0),
        "rows":batch.get("rows",[]),"manager_pdf_ready":bool(batch.get("manager_pdf"))
    }


@loan_web_app.get("/api/manager/report/{batch_id}")
async def manager_report(batch_id:str):
    with MANAGER_LOCK:
        batch=MANAGER_BATCHES.get(batch_id)

    path=Path(batch.get("manager_pdf")) if batch and batch.get("manager_pdf") else None
    if not path or not path.exists():
        return JSONResponse(status_code=404,content={"status":"ERROR","message":"Manager report is not ready."})

    return FileResponse(
        str(path),media_type="application/pdf",
        filename=f"{batch_id}_manager_report.pdf"
    )


@loan_web_app.get("/api/manager/application/{batch_id}/{index}")
async def manager_application_report(batch_id:str,index:int):
    try:
        path,application_id=_manager_individual_pdf(batch_id,index)
        if not path or not Path(path).exists():
            return JSONResponse(status_code=404,content={"status":"ERROR","message":"Application report is not available."})

        safe_id=re.sub(r"[^A-Za-z0-9._-]+","_",str(application_id or f"application_{index+1}"))
        return FileResponse(
            path,media_type="application/pdf",
            filename=f"{safe_id}_assessment.pdf"
        )
    except Exception as exc:
        return JSONResponse(status_code=500,content={"status":"ERROR","message":f"Unable to generate application report: {exc}"})


@loan_web_app.get("/api/manager/template")
async def manager_template():
    out_dir=BASE_DIR/"manager_reports"
    out_dir.mkdir(parents=True,exist_ok=True)
    path=out_dir/"Mortgage_Manager_Excel_Template.xlsx"
    if not path.exists():
        pd.DataFrame(columns=MANAGER_TEMPLATE_COLUMNS).to_excel(path,index=False)

    return FileResponse(
        str(path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name
    )



MANAGER_PAGE = r'''<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Manager Command Center — Gen AI Mortgage</title>
<style>
:root{--bg:#03101d;--text:#f5f9ff;--text2:#d9e8f4;--muted:#8ea8ba;--muted2:#638096;--line:rgba(157,207,235,.14);--line2:rgba(91,190,255,.28);--cyan:#55e0d0;--blue:#58baff;--blue2:#2e87ff;--green:#55e5a0;--red:#ff7184;--amber:#ffd36a;--r:24px;--shadow:0 30px 90px rgba(0,0,0,.38)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;min-height:100vh;color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Arial,sans-serif;background:radial-gradient(circle at 8% 4%,rgba(26,116,172,.35),transparent 27%),radial-gradient(circle at 92% 10%,rgba(64,91,190,.25),transparent 25%),linear-gradient(145deg,#02070d,#061827 46%,#02070d);overflow-x:hidden}
body:before{content:'';position:fixed;inset:0;pointer-events:none;background-image:linear-gradient(rgba(107,191,238,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(107,191,238,.035) 1px,transparent 1px);background-size:44px 44px;mask-image:linear-gradient(to bottom,#000,transparent 90%)}
.shell{position:relative;z-index:1;width:min(1500px,calc(100% - 32px));margin:0 auto;padding:22px 0 48px}.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:26px}.brand{display:flex;align-items:center;gap:12px}.brand-mark{width:42px;height:42px;border-radius:14px;display:grid;place-items:center;background:linear-gradient(145deg,rgba(81,190,255,.2),rgba(66,111,255,.14));border:1px solid var(--line2);box-shadow:0 0 35px rgba(57,166,255,.14);font-size:19px}.brand small{display:block;color:var(--cyan);font-size:10px;font-weight:800;letter-spacing:.2em}.brand strong{display:block;font-size:15px}.top-actions{display:flex;gap:10px}.nav-btn,.button{border:1px solid var(--line2);color:var(--text);text-decoration:none;background:rgba(11,31,50,.72);padding:11px 15px;border-radius:13px;font-weight:750;font-size:12px;cursor:pointer;transition:.25s}.nav-btn:hover,.button:hover{transform:translateY(-2px);border-color:rgba(125,211,252,.55);box-shadow:0 12px 30px rgba(0,0,0,.22)}
.hero{position:relative;overflow:hidden;display:grid;grid-template-columns:1.35fr .65fr;gap:20px;padding:34px;border:1px solid var(--line);border-radius:30px;background:linear-gradient(135deg,rgba(12,35,57,.86),rgba(6,19,33,.72));box-shadow:var(--shadow);backdrop-filter:blur(18px)}.hero:after{content:'';position:absolute;top:0;bottom:0;width:30%;background:linear-gradient(90deg,transparent,rgba(111,214,255,.08),transparent);transform:translateX(-120%);}.eyebrow{color:var(--cyan);font-size:10px;font-weight:850;letter-spacing:.22em;text-transform:uppercase}.hero h1{font-size:clamp(34px,5vw,66px);line-height:.98;margin:12px 0 16px;letter-spacing:-.045em}.hero h1 span{background:linear-gradient(90deg,#fff,#80d5ff 55%,#79a8ff);-webkit-background-clip:text;background-clip:text;color:transparent}.hero p{max-width:780px;color:var(--muted);font-size:14px;line-height:1.7;margin:0}.hero-visual{position:relative;min-height:210px;display:grid;place-items:center}
.section{margin-top:20px}.section-head{display:flex;justify-content:space-between;align-items:end;gap:18px;margin:0 2px 12px}.section-head h2{margin:0;font-size:17px}.section-head p{margin:5px 0 0;color:var(--muted);font-size:12px}.tag{font-size:10px;color:var(--cyan);padding:7px 10px;border:1px solid var(--line2);border-radius:999px;background:rgba(50,147,210,.08)}.card{border:1px solid var(--line);background:linear-gradient(145deg,rgba(12,31,50,.78),rgba(5,17,29,.72));border-radius:var(--r);box-shadow:0 18px 60px rgba(0,0,0,.22);backdrop-filter:blur(16px)}
.upload-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.upload-card,.process-card,.info-card{padding:22px}.drop{border:1px dashed rgba(102,199,249,.3);border-radius:18px;padding:25px;text-align:center;background:rgba(64,166,219,.045);transition:.25s}.drop:hover,.drop.drag{border-color:rgba(102,199,249,.75);background:rgba(64,166,219,.09);box-shadow:inset 0 0 35px rgba(70,180,240,.05)}.drop-icon{font-size:30px;margin-bottom:9px}.drop strong{display:block;font-size:15px}.drop span{display:block;color:var(--muted);font-size:11px;margin-top:6px}.file-name{margin:13px 0;color:var(--text2);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.actions{display:flex;gap:9px;flex-wrap:wrap}.primary{background:linear-gradient(135deg,#3197ff,#4e72ff);border-color:rgba(128,209,255,.4);box-shadow:0 10px 28px rgba(48,125,255,.2)}.secondary{background:rgba(11,32,52,.85)}button:disabled{opacity:.45;cursor:not-allowed;transform:none!important}.micro{color:var(--muted2);font-size:10px;line-height:1.55;margin-top:12px}.process-top{display:flex;justify-content:space-between;gap:15px;align-items:center}.status-line{font-size:13px;font-weight:750}.pct{font-size:24px;font-weight:850;color:var(--cyan)}.bar{height:9px;border-radius:99px;background:rgba(255,255,255,.06);overflow:hidden;margin-top:14px}.fill{height:100%;width:0;background:linear-gradient(90deg,var(--blue2),var(--cyan));box-shadow:0 0 22px rgba(85,224,208,.4);transition:width .4s}.msg{min-height:18px;margin-top:10px;color:var(--amber);font-size:11px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin-top:15px}.kpi{position:relative;padding:18px;overflow:hidden}.kpi:after{content:'';position:absolute;width:90px;height:90px;border-radius:50%;right:-35px;top:-35px;background:rgba(85,224,208,.08);filter:blur(2px)}.kpi-label{color:var(--muted);font-size:10px;letter-spacing:.13em;text-transform:uppercase}.kpi-value{font-size:31px;font-weight:850;margin-top:5px;letter-spacing:-.04em}.kpi.ap .kpi-value{color:var(--green)}.kpi.de .kpi-value{color:var(--red)}.kpi.hr .kpi-value{color:var(--amber)}
.results{padding:0;overflow:hidden}.results-head{padding:22px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:16px}.results-title strong{display:block;font-size:16px}.results-title span{display:block;color:var(--muted);font-size:11px;margin-top:4px}.searchbox{position:relative;min-width:min(430px,100%)}.searchbox input{width:100%;border:1px solid var(--line2);border-radius:14px;background:rgba(2,12,22,.68);color:var(--text);padding:13px 42px 13px 40px;outline:none;font-size:12px}.searchbox input:focus{border-color:rgba(102,207,255,.75);box-shadow:0 0 0 3px rgba(74,174,255,.08)}.search-icon{position:absolute;left:14px;top:10px;color:var(--muted);font-size:17px}.clear-search{position:absolute;right:9px;top:6px;border:0;background:transparent;color:var(--muted);font-size:18px;cursor:pointer}.result-count{padding:10px 22px;color:var(--muted);font-size:10px;border-bottom:1px solid rgba(255,255,255,.05)}.table-wrap{overflow:auto}.table-wrap table{width:100%;border-collapse:collapse;min-width:1050px}.table-wrap th{padding:12px 14px;text-align:left;font-size:9px;letter-spacing:.13em;color:#9fc2d7;background:rgba(5,18,31,.95);position:sticky;top:0;z-index:2}.table-wrap td{padding:13px 14px;border-top:1px solid rgba(157,207,235,.08);font-size:11px;color:var(--text2);vertical-align:top}.table-wrap tr{transition:.18s}.table-wrap tbody tr:hover{background:rgba(79,183,235,.055)}.id-link{color:#78d4ff;text-decoration:none;font-weight:850;white-space:nowrap}.id-link:hover{text-decoration:underline;color:#fff}.applicant{font-weight:750}.reason{max-width:340px;color:#c9d9e4;line-height:1.45}.summary{max-width:350px;color:var(--muted);line-height:1.45}.badge{display:inline-flex;align-items:center;gap:6px;padding:6px 9px;border-radius:999px;font-size:9px;font-weight:850;letter-spacing:.06em;white-space:nowrap}.badge:before{content:'';width:6px;height:6px;border-radius:50%;background:currentColor;box-shadow:0 0 10px currentColor}.badge.a{color:var(--green);background:rgba(85,229,160,.09);border:1px solid rgba(85,229,160,.2)}.badge.d{color:var(--red);background:rgba(255,113,132,.08);border:1px solid rgba(255,113,132,.2)}.badge.r{color:var(--amber);background:rgba(255,211,106,.08);border:1px solid rgba(255,211,106,.2)}.badge.q{color:var(--cyan);background:rgba(85,224,208,.07);border:1px solid rgba(85,224,208,.18)}.empty{padding:40px 22px;text-align:center;color:var(--muted);font-size:12px}.hidden{display:none!important}.report-area{padding:18px 22px;border-top:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}.report-note{color:var(--muted);font-size:11px}.report-note b{color:var(--text2)}
.lower{display:grid;grid-template-columns:1fr 1fr;gap:18px}.info-card h3{margin:0 0 16px;font-size:14px}.step{display:grid;grid-template-columns:34px 1fr;gap:11px;padding:12px 0;border-top:1px solid rgba(255,255,255,.06)}.step:first-child{border-top:0}.num{width:30px;height:30px;border-radius:10px;display:grid;place-items:center;background:rgba(76,178,240,.08);border:1px solid var(--line2);color:var(--cyan);font-size:10px;font-weight:850}.step b{font-size:11px}.step span{display:block;color:var(--muted);font-size:10px;line-height:1.5;margin-top:3px}.band{display:grid;grid-template-columns:110px 1fr;gap:12px;align-items:start;padding:12px 0;border-top:1px solid rgba(255,255,255,.06)}.band:first-of-type{border-top:0}.band b{font-size:10px}.band span{color:var(--muted);font-size:10px;line-height:1.5}.band.ap b{color:var(--green)}.band.hr b{color:var(--amber)}.band.de b{color:var(--red)}.notice{margin-top:15px;padding:12px;border-radius:13px;background:rgba(255,211,106,.045);border:1px solid rgba(255,211,106,.12);color:var(--muted);font-size:10px;line-height:1.55}.footer{text-align:center;color:#557083;font-size:9px;margin-top:24px;letter-spacing:.08em}
@media(max-width:1050px){.hero{grid-template-columns:1fr}.hero-visual{min-height:150px}.upload-grid,.lower{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,1fr)}}@media(max-width:700px){.shell{width:min(100% - 20px,1500px);padding-top:12px}.topbar{align-items:flex-start}.top-actions .nav-btn:last-child{display:none}.hero{padding:23px;border-radius:23px}.hero h1{font-size:38px}.hero-visual{display:none}.kpis{grid-template-columns:1fr 1fr}.kpi{padding:14px}.kpi-value{font-size:25px}.results-head{align-items:stretch;flex-direction:column}.searchbox{min-width:0}.upload-card,.process-card,.info-card{padding:17px}.actions .button{flex:1;text-align:center}.band{grid-template-columns:95px 1fr}}@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
\n/* LIGHTWEIGHT HOME VISUAL LAYER */
<style>
/* ============================================================
   LOW-CPU CINEMATIC MODE
   Keeps the visual identity while avoiding permanent GPU/CPU loops.
   ============================================================ */
@media (max-width: 900px){
  .cinematic-cursor,.cinematic-cursor-bubble{display:none !important;}
  .cinematic-light-sweep{opacity:.55;}
  .home-house{will-change:auto !important;}
}
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation-duration:.001ms !important;animation-iteration-count:1 !important;transition-duration:.001ms !important;scroll-behavior:auto !important;}
  .cinematic-cursor,.cinematic-cursor-bubble{display:none !important;}
}

/* ============================================================
   LIGHTWEIGHT DEVICE MODE — intentional minimal motion
   No custom cursor, no particle trail, no permanent animation loops.
   The home/door hover remains the single interactive visual.
   ============================================================ */
body:before{animation:none!important}
.cinematic-cursor,.cinematic-cursor-bubble,.cinematic-particles,.cinematic-light-sweep,.orb{display:none!important}
.home-window,.home-beacon,.home-house,.house-glow{animation:none!important;will-change:auto!important}
.home-door-hit:hover .home-door{filter:brightness(1.08);box-shadow:inset 0 0 12px rgba(89,185,255,.08),0 0 14px rgba(89,185,255,.08)}
.card{backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}
@media (max-width:900px){.card{backdrop-filter:blur(7px);-webkit-backdrop-filter:blur(7px)}.hero,.upload-card,.process-card,.info-card{box-shadow:0 14px 38px rgba(0,0,0,.22)}}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}.home-door-hit:hover .home-door{transform:none!important}}
</style></style></head>
<body><div class='shell'>
<header class='topbar'><div class='brand'><div class='brand-mark'>⌂</div><div><small>GEN AI MORTGAGE</small><strong>Manager Command Center</strong></div></div><div class='top-actions'><a class='nav-btn' href='/'>← Individual Application</a><a class='nav-btn' href='#resultsPanel'>Portfolio Results</a></div></header>
<section class='hero'><div><div class='eyebrow'>02 · Portfolio Intelligence</div><h1>Review hundreds of loans<br><span>at a single glance.</span></h1><p>Upload a structured Excel portfolio, run the Manager screening layer, inspect decision reasons, search any application instantly, and open an individual assessment PDF directly from its Application ID.</p></div><div class='hero-visual'><div class='house-scene'><div class='house-glow'></div><div class='home-house'><div class='home-roof'></div><div class='home-chimney'></div><div class='home-body'><div class='home-window'></div><div class='home-window two'></div><div class='home-door-hit' title='Open home'><div class='home-door'></div></div></div><div class='home-beacon'></div><div class='home-sign'>MORTGAGE HOME</div></div><div class='home-caption'>PORTFOLIO • HOME • LOANS</div></div></div></section>
<section class='section'><div class='section-head'><div><h2>01 · Load Portfolio</h2><p>Excel rows are normalized into individual manager assessments.</p></div><span class='tag'>MAX 500 APPLICATIONS</span></div><div class='upload-grid'>
<div class='card upload-card'><div class='drop' id='dropZone'><div class='drop-icon'>⇧</div><strong>Drop your Excel portfolio here</strong><span>.xlsx or .xls · one applicant per row</span><input id='excel' type='file' accept='.xlsx,.xls' hidden></div><div class='file-name' id='fileName'>No file selected</div><div class='actions'><button class='button secondary' type='button' onclick="document.getElementById('excel').click()">Choose Excel</button><button class='button secondary' type='button' onclick='downloadTemplate()'>Download Template</button></div></div>
<div class='card process-card'><div class='process-top'><div><div class='eyebrow'>Manager Screening Engine</div><div class='status-line' id='status'>Ready for portfolio upload</div></div><div class='pct' id='pct'>0%</div></div><div class='bar'><div class='fill' id='fill'></div></div><div class='msg' id='msg'></div><button class='button primary' id='startBtn' type='button' onclick='startBatch()' style='width:100%;margin-top:12px'>Start Portfolio Assessment →</button><div class='micro'>Automated manager triage checks affordability, LTV, income, age, employment and mandatory data. It does not replace lender underwriting or verification.</div></div></div></section>
<section class='section hidden' id='resultsPanel'><div class='section-head'><div><h2>02 · Portfolio Results</h2><p>Decision intelligence updates live while the portfolio is being assessed.</p></div><span class='tag' id='batchTag'>BATCH</span></div><div class='kpis'><div class='card kpi'><div class='kpi-label'>Total Applications</div><div class='kpi-value' id='tot'>0</div></div><div class='card kpi ap'><div class='kpi-label'>Approved</div><div class='kpi-value' id='app'>0</div></div><div class='card kpi de'><div class='kpi-label'>Declined</div><div class='kpi-value' id='dec'>0</div></div><div class='card kpi hr'><div class='kpi-label'>Human Review</div><div class='kpi-value' id='rev'>0</div></div></div>
<div class='card results' style='margin-top:15px'><div class='results-head'><div class='results-title'><strong>Application Intelligence</strong><span>Search below by Application ID or applicant name.</span></div><div class='searchbox'><span class='search-icon'>⌕</span><input id='search' placeholder='Search Application ID or applicant…' oninput='renderRows()'><button class='clear-search' type='button' onclick='clearSearch()'>×</button></div></div><div class='result-count' id='resultCount'>0 applications</div><div id='tableWrap' class='table-wrap hidden'><table><thead><tr><th>APPLICATION ID</th><th>APPLICANT</th><th>STATUS</th><th>FOIR</th><th>LTV</th><th>WHY</th><th>SUMMARY</th></tr></thead><tbody id='tbody'></tbody></table></div><div id='empty' class='empty'>Assessment results will appear here.</div><div id='reportArea' class='report-area hidden'><div class='report-note'>Click an <b>Application ID</b> to open its individual assessment PDF.</div><a id='reportLink' class='button primary'>Download Consolidated Manager PDF →</a></div></div></section>
<section class='section lower'><div class='card info-card'><h3>03 · Manager Workflow</h3><div class='step'><div class='num'>01</div><div><b>Excel ingestion</b><span>Validate, normalize and retain every source applicant field.</span></div></div><div class='step'><div class='num'>02</div><div><b>Data integrity gate</b><span>Missing mandatory applicant or loan data routes to Human Review.</span></div></div><div class='step'><div class='num'>03</div><div><b>Affordability + collateral</b><span>Calculate proposed EMI, FOIR and loan-to-value.</span></div></div><div class='step'><div class='num'>04</div><div><b>Decision routing</b><span>Separate hard exceptions from borderline review cases.</span></div></div><div class='step'><div class='num'>05</div><div><b>Manager reporting</b><span>Download one consolidated PDF or drill into any application.</span></div></div></div>
<div class='card info-card'><h3>Decision Bands</h3><div class='band ap'><b>APPROVED</b><span>Complete mandatory data and passes configured automated screening without review flags.</span></div><div class='band hr'><b>HUMAN REVIEW</b><span>Missing/invalid mandatory data, borderline affordability/LTV, short employment history or document concerns.</span></div><div class='band de'><b>DECLINED</b><span>Hard exception such as severe FOIR, income, age, LTV or loan-range failure.</span></div><div class='notice'><b>Important:</b> These are configurable manager-demo screening bands. They are not a substitute for lender policy, KYC, document verification, credit bureau checks or final underwriting.</div></div></section>
<div class='footer'>GEN AI MORTGAGE · MANAGER COMMAND CENTER · INDIVIDUAL APPLICATION WORKFLOW REMAINS UNCHANGED</div></div>

<script>
let currentBatch=null,rows=[];const input=document.getElementById('excel'),drop=document.getElementById('dropZone');input.addEventListener('change',()=>{document.getElementById('fileName').textContent=input.files[0]?.name||'No file selected'});['dragenter','dragover'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('drag')}));['dragleave','drop'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('drag')}));drop.addEventListener('drop',e=>{const f=e.dataTransfer.files?.[0];if(f){try{const dt=new DataTransfer();dt.items.add(f);input.files=dt.files;document.getElementById('fileName').textContent=f.name}catch(_){}}});
function downloadTemplate(){window.open('/api/manager/template','_blank')}function clearSearch(){document.getElementById('search').value='';renderRows();document.getElementById('search').focus()}function esc(v){return String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}function badge(status){const s=(status||'QUEUED').toUpperCase(),c=s==='APPROVED'?'a':s==='DECLINED'?'d':s==='HUMAN REVIEW'?'r':'q';return `<span class='badge ${c}'>${esc(s)}</span>`}
function renderRows(){const q=(document.getElementById('search').value||'').toLowerCase().trim(),filtered=rows.filter(x=>!q||String(x.application_id||'').toLowerCase().includes(q)||String(x.applicant||'').toLowerCase().includes(q));document.getElementById('tbody').innerHTML=filtered.map(x=>{const idx=Number(x.index),href='/api/manager/application/'+encodeURIComponent(currentBatch)+'/'+idx;return `<tr><td><a class='id-link' href='${href}' target='_blank' rel='noopener' title='Open individual assessment PDF'>${esc(x.application_id)}</a></td><td class='applicant'>${esc(x.applicant)}</td><td>${badge(x.status)}</td><td>${x.foir==null?'—':esc(x.foir)+'%'}</td><td>${x.ltv==null?'—':esc(x.ltv)+'%'}</td><td class='reason'>${esc(x.reason||'Processing…')}</td><td class='summary'>${esc(x.summary||'Awaiting assessment…')}</td></tr>`}).join('');document.getElementById('resultCount').textContent=filtered.length+' of '+rows.length+' applications';document.getElementById('empty').classList.toggle('hidden',filtered.length>0);document.getElementById('tableWrap').classList.toggle('hidden',filtered.length===0)}
async function startBatch(){const msg=document.getElementById('msg');if(!input.files.length){msg.textContent='Please choose an Excel file first.';return}const btn=document.getElementById('startBtn');btn.disabled=true;btn.textContent='Uploading…';msg.textContent='';const fd=new FormData();fd.append('file',input.files[0]);try{const r=await fetch('/api/manager/upload',{method:'POST',body:fd}),d=await r.json();if(!r.ok||d.status==='ERROR')throw Error(d.message||'Upload failed');currentBatch=d.batch_id;rows=[];document.getElementById('resultsPanel').classList.remove('hidden');document.getElementById('batchTag').textContent=d.batch_id||'BATCH';document.getElementById('tot').textContent=d.total;document.getElementById('tableWrap').classList.remove('hidden');document.getElementById('empty').classList.add('hidden');document.getElementById('reportArea').classList.add('hidden');document.getElementById('search').value='';btn.textContent='Assessment Running…';document.getElementById('resultsPanel').scrollIntoView({behavior:'smooth',block:'start'});poll()}catch(e){msg.textContent=e.message;btn.disabled=false;btn.textContent='Start Portfolio Assessment →'}}
async function poll(){if(!currentBatch)return;try{const r=await fetch('/api/manager/status/'+encodeURIComponent(currentBatch),{cache:'no-store'}),d=await r.json();if(!r.ok)throw Error(d.message||'Status unavailable');rows=d.rows||[];document.getElementById('status').textContent=d.message||d.status;document.getElementById('pct').textContent=(d.progress||0)+'%';document.getElementById('fill').style.width=(d.progress||0)+'%';document.getElementById('tot').textContent=d.total||0;document.getElementById('app').textContent=d.approved||0;document.getElementById('dec').textContent=d.declined||0;document.getElementById('rev').textContent=d.human_review||0;renderRows();if(d.status==='COMPLETED'){document.getElementById('startBtn').disabled=false;document.getElementById('startBtn').textContent='Start New Portfolio →';if(d.manager_pdf_ready){document.getElementById('reportArea').classList.remove('hidden');document.getElementById('reportLink').href='/api/manager/report/'+encodeURIComponent(currentBatch)}return}if(d.status==='ERROR'){document.getElementById('startBtn').disabled=false;document.getElementById('startBtn').textContent='Retry Portfolio Assessment →';return}setTimeout(poll,900)}catch(e){document.getElementById('status').textContent=e.message;setTimeout(poll,2500)}}
</script></body></html>'''



# ============================================================
# RENDER / PRODUCTION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    uvicorn.run(
        loan_web_app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True,
    )


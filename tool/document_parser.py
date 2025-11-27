"""
Main document parser module for extracting topic information from source folders
"""

import os
from pathlib import Path
from typing import List, Dict
from .extractors import DocumentExtractor
from .schema import (
    TopicData,
    ParsedDocuments,
    DocumentMetadata,
    identify_document_type
)


class TopicParser:
    """Parser for extracting and organizing topic documents"""

    def __init__(self, source_dir: str = "source", output_dir: str = "output"):
        """
        Initialize TopicParser

        Args:
            source_dir: Directory containing topic folders
            output_dir: Directory where JSON outputs will be saved
        """
        self.source_dir = source_dir
        self.output_dir = output_dir

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def list_topics(self) -> List[str]:
        """
        List all available topic folders in source directory

        Returns:
            List of topic folder names
        """
        if not os.path.exists(self.source_dir):
            return []

        topics = []
        for item in os.listdir(self.source_dir):
            item_path = os.path.join(self.source_dir, item)
            if os.path.isdir(item_path):
                topics.append(item)

        return topics

    def parse_topic(self, topic_name: str, save_output: bool = True) -> TopicData:
        """
        Parse all documents in a topic folder

        Args:
            topic_name: Name of the topic folder
            save_output: Whether to save JSON output to file

        Returns:
            TopicData object containing all parsed documents

        Raises:
            FileNotFoundError: If topic folder doesn't exist
        """
        topic_path = os.path.join(self.source_dir, topic_name)

        if not os.path.exists(topic_path):
            raise FileNotFoundError(f"Topic folder not found: {topic_path}")

        if not os.path.isdir(topic_path):
            raise ValueError(f"Path is not a directory: {topic_path}")

        # Get all files in the topic folder
        files = self._get_files_in_folder(topic_path)

        if not files:
            raise ValueError(f"No supported files found in topic folder: {topic_path}")

        # Parse documents
        parsed_docs = self._parse_documents(files)

        # Create metadata
        metadata = self._create_metadata(topic_name, files, parsed_docs)

        # Create TopicData
        topic_data = TopicData(
            topic=topic_name,
            documents=parsed_docs,
            metadata=metadata
        )

        # Note: save_output parameter kept for API compatibility but not used
        # Output saving is now handled by main.py workflow
        return topic_data

    def _get_files_in_folder(self, folder_path: str) -> List[str]:
        """Get all supported files in a folder"""
        supported_extensions = ['.pdf', '.docx']
        files = []

        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)

            if os.path.isfile(file_path):
                ext = Path(filename).suffix.lower()
                if ext in supported_extensions:
                    files.append(file_path)

        return files

    def _parse_documents(self, files: List[str]) -> ParsedDocuments:
        """
        Parse all files and organize by document type

        Args:
            files: List of file paths

        Returns:
            ParsedDocuments object
        """
        documents = ParsedDocuments()

        for file_path in files:
            filename = os.path.basename(file_path)
            doc_type = identify_document_type(filename)

            if doc_type is None:
                print(f"[WARN] Could not identify document type for: {filename}")
                continue

            # Extract text
            text = DocumentExtractor.extract_text(file_path)

            if text is None:
                print(f"[WARN] Failed to extract text from: {filename}")
                continue

            # Assign to appropriate field (only if not already assigned)
            current_value = getattr(documents, doc_type)

            if current_value is None:
                setattr(documents, doc_type, text)
                print(f"[OK] Parsed {doc_type}: {filename}")
            else:
                # Multiple files of same type - append with separator
                combined_text = current_value + "\n\n--- ADDITIONAL DOCUMENT ---\n\n" + text
                setattr(documents, doc_type, combined_text)
                print(f"[OK] Appended to {doc_type}: {filename}")

        return documents

    def _create_metadata(self, topic_name: str, files: List[str],
                        parsed_docs: ParsedDocuments) -> DocumentMetadata:
        """Create metadata for the parsed topic"""
        missing_documents = []

        # Check which documents are missing
        for field_name in ['product_roadmap', 'engineering_ticket',
                          'meeting_transcript', 'marketing_notes', 'customer_feedback']:
            if getattr(parsed_docs, field_name) is None:
                missing_documents.append(field_name)

        return DocumentMetadata(
            topic_folder=topic_name,
            file_count=len(files),
            missing_documents=missing_documents
        )


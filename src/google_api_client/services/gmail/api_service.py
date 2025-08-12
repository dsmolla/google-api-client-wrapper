import base64
import os
from typing import Optional, List, Dict, Any

from googleapiclient.errors import HttpError

from ...utils.datetime import convert_datetime_to_readable
from ...utils.log_sanitizer import sanitize_for_logging
import logging

from .types import EmailMessage, EmailAttachment, Label, EmailThread
from .query_builder import EmailQueryBuilder
from . import utils
from .constants import DEFAULT_MAX_RESULTS, MAX_RESULTS_LIMIT

logger = logging.getLogger(__name__)

# Import exceptions from centralized location
from .exceptions import GmailError, GmailPermissionError, AttachmentNotFoundError


class GmailApiService:
    """
    Service layer for Gmail API operations.
    Contains all Gmail API functionality that was removed from dataclasses.
    """
    
    def __init__(self, service: Any):
        """
        Initialize Gmail service.
        
        Args:
            service: The Gmail API service instance
        """
        self._service = service

    def query(self) -> EmailQueryBuilder:
        """
        Create a new EmailQueryBuilder for building complex email queries with a fluent API.

        Returns:
            EmailQueryBuilder instance for method chaining

        Example:
            emails = (EmailMessage.query()
                .limit(50)
                .from_sender("sender@example.com")
                .search("meeting")
                .with_attachments()
                .execute())
        """
        from .query_builder import EmailQueryBuilder
        return EmailQueryBuilder(self)

    def list_emails(
            self,
            max_results: Optional[int] = DEFAULT_MAX_RESULTS,
            query: Optional[str] = None,
            include_spam_trash: bool = False,
            label_ids: Optional[List[str]] = None
    ) -> List[EmailMessage]:
        """
        Fetches a list of messages from Gmail with optional filtering.

        Args:
            max_results: Maximum number of messages to retrieve. Defaults to 30.
            query: Gmail search query string (same syntax as Gmail search).
            include_spam_trash: Whether to include messages from spam and trash.
            label_ids: List of label IDs to filter by.

        Returns:
            A list of EmailMessage objects representing the messages found.
            If no messages are found, an empty list is returned.
        """
        # Input validation
        if max_results and (max_results < 1 or max_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")

        sanitized = sanitize_for_logging(query=query, max_results=max_results,
                                         include_spam_trash=include_spam_trash, label_ids=label_ids)
        logger.info("Fetching messages with max_results=%s, query=%s, include_spam_trash=%s, label_ids=%s",
                    sanitized['max_results'], sanitized['query'], sanitized['include_spam_trash'],
                    sanitized['label_ids'])


        # Get list of message IDs
        request_params = {
            'userId': 'me',
            'maxResults': max_results,
            'includeSpamTrash': include_spam_trash
        }

        if query:
            request_params['q'] = query
        if label_ids:
            request_params['labelIds'] = label_ids

        try:
            result = self._service.users().messages().list(**request_params).execute()
            messages = result.get('messages', [])

            logger.info("Found %d message IDs", len(messages))

            # Fetch full message details
            email_messages = []
            for message in messages:
                try:
                    email_messages.append(self.get_email(message['id']))
                except Exception as e:
                    logger.warning("Failed to fetch message: %s", e)

            logger.info("Successfully fetched %d complete messages", len(email_messages))
            return email_messages

        except Exception as e:
            logger.error("An error occurred while fetching messages: %s", e)
            raise

    def get_email(self, message_id: str) -> EmailMessage:
        """
        Retrieves a specific message from Gmail using its unique identifier.

        Args:
            message_id: The unique identifier of the message to be retrieved.

        Returns:
            An EmailMessage object representing the message with the specified ID.
        """
        logger.info("Retrieving message with ID: %s", message_id)

        try:
            gmail_message = self._service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            logger.info("Message retrieved successfully")
            return utils.from_gmail_message(gmail_message)
        except Exception as e:
            logger.error("Error retrieving message: %s", e)
            raise

    def send_email(
            self,
            to: List[str],
            subject: Optional[str] = None,
            body_text: Optional[str] = None,
            body_html: Optional[str] = None,
            cc: Optional[List[str]] = None,
            bcc: Optional[List[str]] = None,
            attachment_paths: Optional[List[str]] = None,
            reply_to_message_id: Optional[str] = None,
            references: Optional[str] = None,
            thread_id: Optional[str] = None
    ) -> EmailMessage:
        """
        Sends a new email message.

        Args:
            to: List of recipient email addresses.
            subject: The subject line of the email.
            body_text: Plain text body of the email (optional).
            body_html: HTML body of the email (optional).
            cc: List of CC recipient email addresses (optional).
            bcc: List of BCC recipient email addresses (optional).
            attachment_paths: List of file paths to attach (optional).
            reply_to_message_id: ID of message this is replying to (optional).
            references: List of references to attach (optional).
            thread_id: ID of the thread to which this message belongs (optional).

        Returns:
            An EmailMessage object representing the message sent.
        """
        sanitized = sanitize_for_logging(subject=subject, to=to)
        logger.info("Sending message with subject=%s, to=%s", sanitized['subject'], sanitized['to'])

        # Create message
        raw_message = utils.create_message(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            attachment_paths=attachment_paths,
            references=references,
            reply_to_message_id=reply_to_message_id
        )


        try:
            send_result = self._service.users().messages().send(
                userId='me',
                body={'raw': raw_message, 'threadId': thread_id}
            ).execute()

            logger.info("Message sent successfully with ID: %s", send_result.get('id'))
            return self.get_email(send_result['id'])

        except Exception as e:
            logger.error("Error sending message: %s", e)
            raise

    def batch_get_emails(self, message_ids: List[str]) -> List["EmailMessage"]:
        """
        Retrieves multiple emails.

        Args:
            message_ids: List of message IDs to retrieve

        Returns:
            List of EmailMessage objects
        """
        logger.info("Batch retrieving %d messages", len(message_ids))

        email_messages = []
        for message_id in message_ids:
            try:
                email_messages.append(self.get_email(message_id))
            except Exception as e:
                logger.warning("Failed to fetch message %s: %s", message_id, e)

        return email_messages

    def batch_send_emails(self, email_data_list: List[Dict[str, Any]]) -> List["EmailMessage"]:
        """
        Sends multiple emails.

        Args:
            email_data_list: List of dictionaries containing email parameters

        Returns:
            List of sent EmailMessage objects
        """
        logger.info("Batch sending %d emails", len(email_data_list))

        sent_messages = []
        for email_data in email_data_list:
            try:
                sent_messages.append(self.send_email(**email_data))
            except Exception as e:
                logger.warning("Failed to send email: %s", e)

        return sent_messages

    def reply(
            self,
            original_email: EmailMessage,
            body_text: Optional[str] = None,
            body_html: Optional[str] = None,
            attachment_paths: Optional[List[str]] = None,
            reply_all: bool = False
    ) -> EmailMessage:
        """
        Sends a reply to the current email message.
        Args:
            original_email: The original email message being replied to
            body_text: Plain text body of the email.
            body_html: HTML body of the email.
            attachment_paths: List of file paths to attach (optional).
            reply_all: A boolean indicating whether to all recipients including cc's.
        Returns:
            An EmailMessage object representing the message sent.
        """
        if original_email.is_from('me'):
            to = original_email.get_recipient_emails()
        else:
            to = [original_email.sender.email]

        logger.info("Replying to message %s", original_email.message_id)
        
        # Build enhanced references header
        enhanced_references = utils.build_references_header(original_email)
        
        return self.send_email(
            to=to,
            subject=original_email.subject,
            body_text=body_text,
            body_html=body_html,
            attachment_paths=attachment_paths,
            reply_to_message_id=original_email.reply_to_id,
            references=enhanced_references,
            thread_id=original_email.thread_id
        )

    def forward(
            self,
            original_email: EmailMessage,
            to: List[str],
            include_attachments: bool = True
    ) -> EmailMessage:
        """
        Forwards an email message to new recipients.
        
        Args:
            original_email: The original email message being forwarded
            to: List of recipient email addresses
            include_attachments: Whether to include original email's attachments
            
        Returns:
            An EmailMessage object representing the forwarded message
        """
        logger.info("Forwarding message %s to %s", original_email.message_id, to)
        
        # Prepare subject with Fwd: prefix
        subject = f"Fwd: {original_email.subject}" if original_email.subject else "Fwd:"

        # Prepare Text body for forwarding
        forwarded_body_text = None
        if original_email.body_text:
            forwarded_body_text = utils.prepare_forward_body_text(original_email)

        # Prepare HTML body for forwarding
        forwarded_body_html = None
        if original_email.body_html:
            forwarded_body_html = utils.prepare_forward_body_html(original_email)

        # Handle original attachments if requested
        attachment_data_list = []
        if include_attachments and original_email.attachments:
            for attachment in original_email.attachments:
                attachment_bytes = self.get_attachment_payload(attachment)
                attachment_data_list.append((attachment.filename, attachment.mime_type, attachment_bytes))

        raw_message = utils.create_message(
            to=to,
            subject=subject,
            body_text=forwarded_body_text,
            body_html=forwarded_body_html,
            attachment_data_list=attachment_data_list if attachment_data_list else None
        )
        
        try:
            send_result = self._service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info("Message forwarded successfully with ID: %s", send_result.get('id'))
            return self.get_email(send_result['id'])
            
        except Exception as e:
            logger.error("Error forwarding message: %s", e)
            raise

    def mark_as_read(self, email: EmailMessage) -> bool:
        """
        Marks a message as read by removing the UNREAD label.

        Args:
            email: The email message being marked as read.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Marking message as read: %s", email.message_id)

        try:
            self._service.users().messages().modify(
                userId='me',
                id=email.message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            email.is_read = True
            logger.info("Message marked as read successfully")
            return True
        except Exception as e:
            logger.error("Error marking message as read: %s", e)
            return False

    def mark_as_unread(self, email: EmailMessage) -> bool:
        """
        Marks a message as unread by adding the UNREAD label.

        Args:
            email: The email message being marked as unread

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Marking message as unread: %s", email.message_id)

        try:
            self._service.users().messages().modify(
                userId='me',
                id=email.message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            email.is_read = False
            logger.info("Message marked as unread successfully")
            return True
        except Exception as e:
            logger.error("Error marking message as unread: %s", e)
            return False

    def add_label(self, email: EmailMessage, labels: List[str]) -> bool:
        """
        Adds labels to a message.

        Args:
            email: The email message to add labels to
            labels: List of label IDs to add.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Adding labels %s to message: %s", labels, email.message_id)


        try:
            self._service.users().messages().modify(
                userId='me',
                id=email.message_id,
                body={'addLabelIds': labels}
            ).execute()
            # Update local state
            for label in labels:
                if label not in email.labels:
                    email.labels.append(label)
                    break
            logger.info("Labels added successfully")
            return True
        except Exception as e:
            logger.error("Error adding labels: %s", e)
            return False

    def remove_label(self, email: EmailMessage, labels: List[str]) -> bool:
        """
        Removes labels from a message.

        Args:
            email: The email message to remove labels from
            labels: List of label IDs to remove.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Removing labels %s from message: %s", labels, email.message_id)

        try:
            self._service.users().messages().modify(
                userId='me',
                id=email.message_id,
                body={'removeLabelIds': labels}
            ).execute()
            # Update local state
            for label in labels:
                try:
                    email.labels.remove(label)
                except ValueError:
                    continue
            logger.info("Labels removed successfully")
            return True
        except Exception as e:
            logger.error("Error removing labels: %s", e)
            return False

    def delete_email(self, email: EmailMessage, permanent: bool = False) -> bool:
        """
        Deletes a message (moves to trash or permanently deletes).

        Args:
            email: The email message being deleted
            permanent: If True, permanently deletes the message. If False, moves to trash.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Deleting message: %s, permanent=%s", email.message_id, permanent)

        try:
            if permanent:
                self._service.users().messages().delete(userId='me', id=email.message_id).execute()
                logger.info("Message permanently deleted")
            else:
                self._service.users().messages().trash(userId='me', id=email.message_id).execute()
                logger.info("Message moved to trash")
            return True
        except Exception as e:
            logger.error("Error deleting message: %s", e)
            return False

    def get_attachment_payload(self, attachment: EmailAttachment) -> bytes:
        attachment_ = self._service.users().messages().attachments().get(
            userId='me',
            messageId=attachment.message_id,
            id=attachment.attachment_id
        ).execute()
        data = attachment_['data']
        data = base64.urlsafe_b64decode(data + '===')

        return data

    def download_attachment(self, attachment: EmailAttachment, download_folder: str = 'attachments'):
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        try:
            logger.info("Downloading attachment %s", attachment.attachment_id)

            with open(os.path.join(download_folder, attachment.filename), 'wb') as f:
                f.write(self.get_attachment_payload(attachment))

            logger.info("Finished downloading attachment %s", attachment.attachment_id)

        except HttpError as e:
            if e.resp.status == 403:
                raise GmailPermissionError(f"Permission denied accessing attachment: {e}")
            elif e.resp.status == 404:
                raise AttachmentNotFoundError(f"Attachment not found: {e}")
            else:
                raise GmailError(f"Gmail API error downloading attachment: {e}")
        except (ValueError, KeyError) as e:
            logger.error("Invalid attachment data format.")
            logger.debug("Attachment data error: %s", str(e)[:100])
            raise GmailError(f"Invalid attachment data: {e}")
        except Exception as e:
            logger.error("Unexpected error downloading attachment.")
            logger.debug("Attachment download error: %s", str(e)[:100])
            raise

    def create_label(self, name: str) -> "Label":
        """
        Creates a new label in Gmail.
        Args:
            name: The name of the label to create.

        Returns:
            A Label object representing the created label including its ID, name, and type.
        """
        logger.info("Creating label with name: %s", name)

        try:
            label = self._service.users().labels().create(
                userId='me',
                body={'name': name, 'type': 'user'}
            ).execute()
            return Label(
                id=label.get('id'),
                name=label.get('name'),
                type=label.get('type', 'user')
            )
        except Exception as e:
            logger.error("Error creating label: %s", e)
            raise

    def list_labels(self) -> List["Label"]:
        """
        Fetches a list of labels from Gmail.
        Returns:
            A list of Label objects representing the labels.
        """
        logger.info("Fetching labels from Gmail")

        try:
            labels_response = self._service.users().labels().list(userId='me').execute()
            labels = labels_response.get('labels', [])
            logger.info("Found %d labels", len(labels))

            labels_list = []
            for label in labels:
                labels_list.append(
                    Label(
                        id=label.get('id'),
                        name=label.get('name'),
                        type=label.get('type')
                    )
                )

            return labels_list

        except Exception as e:
            logger.error("Failed to fetch labels: %s", e)
            raise

    def delete_label(self, label: Label) -> bool:
        """
        Deletes this label.

        Args:
            label: The label to delete.

        Returns:
            True if the label was successfully deleted, False otherwise.
        """
        logger.info("Deleting label with ID: %s", label.id)

        try:
            self._service.users().labels().delete(userId='me', id=label.id).execute()
            logger.info("Label deleted successfully")
            return True
        except Exception as e:
            logger.error("Error deleting label: %s", e)
            return False

    def update_label(self, label: Label, new_name: str) -> "Label":
        """
        Updates the name of this label.
        Args:
            label: The label to update
            new_name: The new name for the label.

        Returns:
            The updated Label object.
        """
        logger.info("Updating label %s to new name: %s", label.id, new_name)

        try:
            updated_label = self._service.users().labels().patch(
                userId='me',
                id=label.id,
                body={'name': new_name}
            ).execute()
            label.name = updated_label.get('name')
            return label
        except Exception as e:
            logger.error("Error updating label: %s", e)
            raise

    def list_threads(
            self,
            max_results: Optional[int] = DEFAULT_MAX_RESULTS,
            query: Optional[str] = None,
            include_spam_trash: bool = False,
            label_ids: Optional[List[str]] = None
    ) -> List[EmailThread]:
        """
        Fetches a list of threads from Gmail with optional filtering.

        Args:
            max_results: Maximum number of threads to retrieve. Defaults to 30.
            query: Gmail search query string (same syntax as Gmail search).
            include_spam_trash: Whether to include threads from spam and trash.
            label_ids: List of label IDs to filter by.

        Returns:
            A list of EmailThread objects representing the threads found.
        """
        # Input validation
        if max_results and (max_results < 1 or max_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")

        sanitized = sanitize_for_logging(query=query, max_results=max_results,
                                         include_spam_trash=include_spam_trash, label_ids=label_ids)
        logger.info("Fetching threads with max_results=%s, query=%s, include_spam_trash=%s, label_ids=%s",
                    sanitized['max_results'], sanitized['query'], sanitized['include_spam_trash'],
                    sanitized['label_ids'])

        # Get list of thread IDs
        request_params = {
            'userId': 'me',
            'maxResults': max_results,
            'includeSpamTrash': include_spam_trash
        }

        if query:
            request_params['q'] = query
        if label_ids:
            request_params['labelIds'] = label_ids

        try:
            result = self._service.users().threads().list(**request_params).execute()
            threads = result.get('threads', [])

            logger.info("Found %d thread IDs", len(threads))

            # Fetch full thread details
            email_threads = []
            for thread in threads:
                try:
                    email_threads.append(self.get_thread(thread['id']))
                except Exception as e:
                    logger.warning("Failed to fetch thread: %s", e)

            logger.info("Successfully fetched %d complete threads", len(email_threads))
            return email_threads

        except Exception as e:
            logger.error("An error occurred while fetching threads: %s", e)
            raise

    def get_thread(self, thread_id: str) -> EmailThread:
        """
        Retrieves a specific thread from Gmail using its unique identifier.

        Args:
            thread_id: The unique identifier of the thread to be retrieved.

        Returns:
            An EmailThread object representing the thread with all its messages.
        """
        logger.info("Retrieving thread with ID: %s", thread_id)

        try:
            gmail_thread = self._service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
            logger.info("Thread retrieved successfully")
            return utils.from_gmail_thread(gmail_thread)
        except Exception as e:
            logger.error("Error retrieving thread: %s", e)
            raise

    def delete_thread(self, thread: EmailThread, permanent: bool = False) -> bool:
        """
        Deletes a thread (moves to trash or permanently deletes).

        Args:
            thread: The EmailThread object being deleted
            permanent: If True, permanently deletes the thread. If False, moves to trash.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Deleting thread: %s, permanent=%s", thread.thread_id, permanent)

        try:
            if permanent:
                self._service.users().threads().delete(userId='me', id=thread.thread_id).execute()
                logger.info("Thread permanently deleted")
            else:
                self._service.users().threads().trash(userId='me', id=thread.thread_id).execute()
                logger.info("Thread moved to trash")
            return True
        except Exception as e:
            logger.error("Error deleting thread: %s", e)
            return False

    def modify_thread_labels(self, thread: EmailThread, add_labels: Optional[List[str]] = None, 
                           remove_labels: Optional[List[str]] = None) -> bool:
        """
        Modifies labels applied to a thread.

        Args:
            thread: The EmailThread object to modify labels for
            add_labels: List of label IDs to add to the thread
            remove_labels: List of label IDs to remove from the thread

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Modifying labels for thread: %s", thread.thread_id)

        if not add_labels and not remove_labels:
            logger.warning("No labels specified for modification")
            return True

        try:
            body = {}
            if add_labels:
                body['addLabelIds'] = add_labels
            if remove_labels:
                body['removeLabelIds'] = remove_labels

            self._service.users().threads().modify(
                userId='me',
                id=thread.thread_id,
                body=body
            ).execute()
            
            logger.info("Thread labels modified successfully")
            return True
        except Exception as e:
            logger.error("Error modifying thread labels: %s", e)
            return False

    def untrash_thread(self, thread: EmailThread) -> bool:
        """
        Removes a thread from trash.

        Args:
            thread: The EmailThread object to untrash

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Untrashing thread: %s", thread.thread_id)

        try:
            self._service.users().threads().untrash(userId='me', id=thread.thread_id).execute()
            logger.info("Thread untrashed successfully")
            return True
        except Exception as e:
            logger.error("Error untrashing thread: %s", e)
            return False


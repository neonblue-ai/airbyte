from dataclasses import dataclass
from typing import Any

import logging
import backoff
import requests
from requests.auth import HTTPBasicAuth
from airbyte_cdk.sources.declarative.auth import DeclarativeOauth2Authenticator
from airbyte_cdk.sources.streams.http.requests_native_auth import Oauth2Authenticator
from airbyte_cdk.sources.streams.http.exceptions import DefaultBackoffException
from airbyte_cdk.utils.airbyte_secrets_utils import add_to_secrets
from airbyte_cdk.utils import AirbyteTracedException
from airbyte_cdk.models import FailureType


logger = logging.getLogger("airbyte")


class KlaviyoOauth2Authenticator(Oauth2Authenticator):
    @backoff.on_exception(
        backoff.expo,
        DefaultBackoffException,
        on_backoff=lambda details: logger.info(
            f"Caught retryable error after {details['tries']} tries. Waiting {details['wait']} seconds then retrying..."
        ),
        max_time=300,
    )
    def _get_refresh_access_token_response(self) -> Any:
        try:
            response = requests.request(
                method="POST",
                url=self.get_token_refresh_endpoint(),
                data=self.build_refresh_request_body(),
                auth=HTTPBasicAuth(
                    self.get_client_id(),
                    self.get_client_secret()
                )
            )
            if response.ok:
                response_json = response.json()
                # Add the access token to the list of secrets so it is replaced before logging the response
                # An argument could be made to remove the prevous access key from the list of secrets, but unmasking values seems like a security incident waiting to happen...
                access_key = response_json.get(self.get_access_token_name())
                if not access_key:
                    raise Exception(
                        "Token refresh API response was missing access token {self.get_access_token_name()}")
                add_to_secrets(access_key)
                self._log_response(response)
                return response_json
            else:
                # log the response even if the request failed for troubleshooting purposes
                self._log_response(response)
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                if e.response.status_code == 429 or e.response.status_code >= 500:
                    raise DefaultBackoffException(
                        request=e.response.request, response=e.response)
            if self._wrap_refresh_token_exception(e):
                message = "Refresh token is invalid or expired. Please re-authenticate from Sources/<your source>/Settings."
                raise AirbyteTracedException(
                    internal_message=message, message=message, failure_type=FailureType.config_error)
            raise
        except Exception as e:
            raise Exception(f"Error while refreshing access token: {e}") from e


@dataclass
class DeclarativeKlaviyoOauth2Authenticator(DeclarativeOauth2Authenticator):
    @backoff.on_exception(
        backoff.expo,
        DefaultBackoffException,
        on_backoff=lambda details: logger.info(
            f"Caught retryable error after {details['tries']} tries. Waiting {details['wait']} seconds then retrying..."
        ),
        max_time=300,
    )
    def _get_refresh_access_token_response(self) -> Any:
        try:
            response = requests.request(
                method="POST",
                url=self.get_token_refresh_endpoint(),
                data=self.build_refresh_request_body(),
                auth=HTTPBasicAuth(
                    self.get_client_id(),
                    self.get_client_secret()
                )
            )
            if response.ok:
                response_json = response.json()
                # Add the access token to the list of secrets so it is replaced before logging the response
                # An argument could be made to remove the prevous access key from the list of secrets, but unmasking values seems like a security incident waiting to happen...
                access_key = response_json.get(self.get_access_token_name())
                if not access_key:
                    raise Exception(
                        "Token refresh API response was missing access token {self.get_access_token_name()}")
                add_to_secrets(access_key)
                self._log_response(response)
                return response_json
            else:
                # log the response even if the request failed for troubleshooting purposes
                self._log_response(response)
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                if e.response.status_code == 429 or e.response.status_code >= 500:
                    raise DefaultBackoffException(
                        request=e.response.request, response=e.response)
            if self._wrap_refresh_token_exception(e):
                message = "Refresh token is invalid or expired. Please re-authenticate from Sources/<your source>/Settings."
                raise AirbyteTracedException(
                    internal_message=message, message=message, failure_type=FailureType.config_error)
            raise
        except Exception as e:
            raise Exception(f"Error while refreshing access token: {e}") from e

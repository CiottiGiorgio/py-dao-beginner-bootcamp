import algokit_utils.logic_error
import pytest
from algokit_utils import (
    ApplicationClient,
    ApplicationSpecification,
    get_localnet_default_account,
)
from algosdk.v2client.algod import AlgodClient

from smart_contracts.dao import contract as dao_contract


@pytest.fixture(scope="session")
def dao_app_spec(algod_client: AlgodClient) -> ApplicationSpecification:
    return dao_contract.app.build(algod_client)


@pytest.fixture(scope="session")
def dao_client(
    algod_client: AlgodClient, dao_app_spec: ApplicationSpecification
) -> ApplicationClient:
    client = ApplicationClient(
        algod_client,
        app_spec=dao_app_spec,
        signer=get_localnet_default_account(algod_client),
        template_values={"UPDATABLE": 1, "DELETABLE": 1},
    )
    return client


PROPOSAL = "This is another proposal."


def test_deploy(dao_client: ApplicationClient):
    dao_client.create(proposal=PROPOSAL)


def test_get_proposal(dao_client: ApplicationClient):
    proposal = dao_client.call(dao_contract.get_proposal).return_value
    assert proposal == PROPOSAL
    assert dao_client.get_global_state()["proposal"] == PROPOSAL


def test_get_votes_negative(dao_client: ApplicationClient):
    with pytest.raises(algokit_utils.logic_error.LogicError):
        dao_client.call(dao_contract.get_votes)


def test_vote_and_get_votes(dao_client: ApplicationClient):
    dao_client.call(dao_contract.vote, in_favor=True)
    votes = dao_client.call(dao_contract.get_votes).return_value
    assert votes[0] == 1
    assert votes[1] == 1

    dao_client.call(dao_contract.vote, in_favor=False)
    votes = dao_client.call(dao_contract.get_votes).return_value
    assert votes[0] == 2
    assert votes[1] == 1

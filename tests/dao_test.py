import algokit_utils.logic_error
import algosdk
import pytest
from algokit_utils import (
    Account,
    ApplicationClient,
    ApplicationSpecification,
    TransactionParameters,
    get_localnet_default_account,
    get_or_create_kmd_wallet_account,
)
from algosdk.v2client.algod import AlgodClient

from smart_contracts.dao import contract as dao_contract


@pytest.fixture(scope="session")
def dao_app_spec(algod_client: AlgodClient) -> ApplicationSpecification:
    return dao_contract.app.build(algod_client)


@pytest.fixture(scope="session")
def creator_account(algod_client: AlgodClient) -> Account:
    return get_localnet_default_account(algod_client)


@pytest.fixture(scope="session")
def dao_client(
    algod_client: AlgodClient,
    dao_app_spec: ApplicationSpecification,
    creator_account: Account,
) -> ApplicationClient:
    client = ApplicationClient(
        algod_client,
        app_spec=dao_app_spec,
        signer=creator_account,
        template_values={"UPDATABLE": 1, "DELETABLE": 1},
    )
    return client


@pytest.fixture(scope="session")
def other_account(algod_client: AlgodClient) -> Account:
    return get_or_create_kmd_wallet_account(
        algod_client, "tealscript-dao-other", 1_000_000_000
    )


PROPOSAL = "This is another proposal."


def test_deploy(dao_client: ApplicationClient):
    dao_client.create(proposal=PROPOSAL)


def test_get_proposal(dao_client: ApplicationClient):
    proposal = dao_client.call(dao_contract.get_proposal).return_value
    assert proposal == PROPOSAL
    assert dao_client.get_global_state()["proposal"] == PROPOSAL


def test_get_registered_asa_negative(dao_client: ApplicationClient):
    with pytest.raises(algokit_utils.logic_error.LogicError):
        dao_client.call(dao_contract.get_registered_asa)


def test_bootstrap_negative(
    dao_client: ApplicationClient, creator_account: Account, other_account: Account
):
    # Fund the contract.
    dao_client.algod_client.send_transactions(
        creator_account.signer.sign_transactions(
            [
                algosdk.transaction.PaymentTxn(
                    creator_account.address,
                    dao_client.algod_client.suggested_params(),
                    dao_client.app_address,
                    200_000,
                )
            ],
            [0],
        )
    )

    sp = dao_client.algod_client.suggested_params()
    sp.fee = 3_000
    sp.flat_fee = True
    with pytest.raises(algokit_utils.logic_error.LogicError):
        dao_client.call(
            dao_contract.bootstrap,
            transaction_parameters=TransactionParameters(
                sender=other_account.address,
                signer=other_account.signer,
                suggested_params=sp,
            ),
        )


def test_bootstrap(dao_client: ApplicationClient):
    # Bootstrap the contract.
    sp = dao_client.algod_client.suggested_params()
    sp.fee = 3_000
    sp.flat_fee = True
    dao_client.call(
        dao_contract.bootstrap,
        transaction_parameters=TransactionParameters(suggested_params=sp),
    )


@pytest.fixture(scope="session")
def registered_asa_id(dao_client: ApplicationClient) -> int:
    return dao_client.call(dao_contract.get_registered_asa).return_value


def test_get_registered_id(dao_client: ApplicationClient, registered_asa_id: int):
    assert registered_asa_id == dao_client.get_global_state()["registered_asa_id"]


def test_vote_negative(
    dao_client: ApplicationClient, other_account: Account, registered_asa_id: int
):
    with pytest.raises(algokit_utils.logic_error.LogicError):
        dao_client.call(
            dao_contract.vote,
            in_favor=True,
            registered_asa=registered_asa_id,
            transaction_parameters=TransactionParameters(
                sender=other_account.address,
                signer=other_account.signer,
            ),
        )


def test_register(
    dao_client: ApplicationClient, other_account: Account, registered_asa_id: int
):
    # Opt-in to the Registered ASA.
    dao_client.algod_client.send_transactions(
        other_account.signer.sign_transactions(
            [
                algosdk.transaction.AssetTransferTxn(
                    other_account.address,
                    dao_client.algod_client.suggested_params(),
                    other_account.address,
                    0,
                    registered_asa_id,
                )
            ],
            [0],
        )
    )

    sp = dao_client.algod_client.suggested_params()
    sp.fee = 3_000
    sp.flat_fee = True
    dao_client.call(
        dao_contract.register,
        registered_asa=registered_asa_id,
        transaction_parameters=TransactionParameters(
            sender=other_account.address,
            signer=other_account.signer,
            suggested_params=sp,
        ),
    )

    with pytest.raises(algosdk.error.AlgodHTTPError):
        dao_client.algod_client.send_transactions(
            other_account.signer.sign_transactions(
                [
                    algosdk.transaction.AssetTransferTxn(
                        other_account.address,
                        dao_client.algod_client.suggested_params(),
                        other_account.address,
                        1,
                        registered_asa_id,
                    )
                ],
                [0],
            )
        )


def test_get_votes_negative(dao_client: ApplicationClient):
    with pytest.raises(algokit_utils.logic_error.LogicError):
        dao_client.call(dao_contract.get_votes)


def test_vote_and_get_votes(
    dao_client: ApplicationClient, other_account: Account, registered_asa_id: int
):
    dao_client.call(
        dao_contract.vote,
        in_favor=True,
        registered_asa=registered_asa_id,
        transaction_parameters=TransactionParameters(
            sender=other_account.address,
            signer=other_account.signer,
        ),
    )
    votes = dao_client.call(dao_contract.get_votes).return_value
    assert votes[0] == 1
    assert votes[1] == 1

    dao_client.call(
        dao_contract.vote,
        in_favor=False,
        registered_asa=registered_asa_id,
        transaction_parameters=TransactionParameters(
            sender=other_account.address,
            signer=other_account.signer,
        ),
    )
    votes = dao_client.call(dao_contract.get_votes).return_value
    assert votes[0] == 2
    assert votes[1] == 1

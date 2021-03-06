# Copyright 2019 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""Integration tests for frontend operations applied to the backend"""
import pytest

import numpy as np

import strawberryfields as sf
from strawberryfields import ops
from strawberryfields.backends import BaseGaussian


# make test deterministic
np.random.random(42)
A = 0.1234
B = -0.543


@pytest.mark.parametrize("gate", ops.gates)
class TestGateApplication:
    """tests that involve gate application"""

    @pytest.fixture
    def G(self, gate):
        """Initialize each gate"""
        if gate in ops.zero_args_gates:
            return gate

        if gate in ops.one_args_gates:
            return gate(A)

        if gate in ops.two_args_gates:
            return gate(A, B)

    def test_gate_dagger_vacuum(self, G, setup_eng, tol):
        """Test applying gate inverses after the gate cancels out"""
        eng, q = setup_eng(2)

        if isinstance(G, (ops.Vgate, ops.Kgate, ops.CKgate)) and isinstance(
            eng.backend, BaseGaussian
        ):
            pytest.skip("Non-Gaussian gates cannot be applied to the Gaussian backend")

        with eng:
            if G.ns == 1:
                G | q[0]
                G.H | q[0]
            elif G.ns == 2:
                G | (q[0], q[1])
                G.H | (q[0], q[1])

        state = eng.run()
        # we must end up back in vacuum since G and G.H cancel each other
        assert np.all(eng.backend.is_vacuum(tol))


class TestChannelApplication:
    """tests that involve channel application"""

    def test_loss_channel(self, setup_eng, tol):
        """Test loss channel with no transmission produces vacuum"""
        eng, q = setup_eng(1)

        with eng:
            ops.Dgate(A) | q[0]
            ops.LossChannel(0) | q[0]

        state = eng.run()
        # we must end up back in vacuum since G and G.H cancel each other
        assert np.all(eng.backend.is_vacuum(tol))

    @pytest.mark.backends("gaussian")
    def test_thermal_loss_channel(self, setup_eng, tol):
        """Test thermal loss channel with no transmission produces thermal state"""
        eng, q = setup_eng(1)
        nbar = 0.43

        with eng:
            ops.Dgate(A) | q[0]
            ops.ThermalLossChannel(0, nbar) | q[0]

        state = eng.run()
        mean_photon, var = state.mean_photon(0)
        assert np.allclose(mean_photon, nbar, atol=tol, rtol=0)
        assert np.allclose(var, nbar ** 2 + nbar, atol=tol, rtol=0)


class TestPreparationApplication:
    """Tests that involve state preparation application"""

    @pytest.mark.backends("tf", "fock")
    def test_ket_state_object(self, setup_eng, pure):
        """Test loading a ket from a prior state object"""
        if not pure:
            pytest.skip("Test only runs on pure states")

        eng, q = setup_eng(1)

        with eng:
            ops.Dgate(0.2) | q[0]

        state1 = eng.run()

        # create new engine
        eng, q = setup_eng(1)

        with eng:
            ops.Ket(state1) | q[0]

        state2 = eng.run()

        # verify it is the same state
        assert state1 == state2

    @pytest.mark.backends("tf", "fock")
    def test_ket_gaussian_state_object(self, setup_eng):
        """Test exception if loading a ket from a Gaussian state object"""
        eng, _ = sf.Engine(1)
        state = eng.run("gaussian")

        # create new engine
        eng, q = setup_eng(1)

        with eng:
            with pytest.raises(ValueError, match="Gaussian states are not supported"):
                ops.Ket(state) | q[0]

    @pytest.mark.backends("tf", "fock")
    def test_ket_mixed_state_object(self, setup_eng, pure):
        """Test exception if loading a ket from a prior mixed state object"""
        if pure:
            pytest.skip("Test only runs on mixed states")

        eng, q = setup_eng(1)

        with eng:
            ops.Dgate(0.2) | q[0]

        state1 = eng.run()

        # create new engine
        eng, q = setup_eng(1)

        with eng:
            with pytest.raises(ValueError, match="Fock state is not pure"):
                ops.Ket(state1) | q[0]

    @pytest.mark.backends("tf", "fock")
    def test_dm_state_object(self, setup_eng, tol):
        """Test loading a density matrix from a prior state object"""
        eng, q = setup_eng(1)

        with eng:
            ops.Dgate(0.2) | q[0]

        state1 = eng.run()

        # create new engine
        eng, q = setup_eng(1)

        with eng:
            ops.DensityMatrix(state1) | q[0]

        state2 = eng.run()

        # verify it is the same state
        assert np.allclose(state1.dm(), state2.dm(), atol=tol, rtol=0)

    @pytest.mark.backends("tf", "fock")
    def test_dm_gaussian_state_object(self, setup_eng):
        """Test exception if loading a ket from a Gaussian state object"""
        eng, _ = sf.Engine(1)
        state = eng.run("gaussian")

        # create new engine
        eng, q = setup_eng(1)

        with eng:
            with pytest.raises(ValueError, match="Gaussian states are not supported"):
                ops.DensityMatrix(state) | q[0]

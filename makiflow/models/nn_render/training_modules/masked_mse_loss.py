# Copyright (C) 2020  Igor Kilbas, Danil Gribanov, Artem Mukhin
#
# This file is part of MakiFlow.
#
# MakiFlow is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MakiFlow is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Foobar.  If not, see <https://www.gnu.org/licenses/>.

import tensorflow as tf
from ..main_modules import NeuralRenderBasis
from makiflow.core.training.loss_builder import Loss
from makiflow.core.training.utils import print_train_info, moving_average
from makiflow.core.training.utils import new_optimizer_used, loss_is_built
from makiflow.generators.nn_render import NNRIterator
from tqdm import tqdm

MASKED_MSE_LOSS = 'MASKED MSE LOSS'


class MaskedMseTrainingModule(NeuralRenderBasis):
    def _prepare_training_vars(self):
        self._masked_mse_loss_is_build = False
        super()._prepare_training_vars()

    def _build_masked_mse_loss(self):
        self._mse_loss = Loss.mse_loss(self._images, self._training_out, raw_tensor=True)
        self._mse_loss = tf.reduce_sum(self._mse_loss * self._mse_mask)
        self._mse_loss = self._mse_loss / tf.reduce_sum(self._mse_mask)
        self._final_masked_mse_loss = self._build_final_loss(self._mse_loss)

    def _setup_masked_mse_loss_inputs(self):
        if self._generator is None:
            raise RuntimeError('The generator is not set.')
        self._mse_mask = self._generator.get_iterator()[NNRIterator.BIN_MASK]

    def _minimize_masked_mse_loss(self, optimizer, global_step):
        if not self._training_vars_are_ready:
            self._prepare_training_vars()

        if not self._masked_mse_loss_is_build:
            self._setup_masked_mse_loss_inputs()
            self._build_masked_mse_loss()
            self._masked_mse_optimizer = optimizer
            self._masked_mse_train_op = optimizer.minimize(
                self._final_masked_mse_loss, var_list=self._trainable_vars, global_step=global_step
            )
            self._session.run(tf.variables_initializer(optimizer.variables()))
            self._masked_mse_loss_is_build = True
            loss_is_built()

        if self._masked_mse_optimizer != optimizer:
            new_optimizer_used()
            self._masked_mse_optimizer = optimizer
            self._masked_mse_train_op = optimizer.minimize(
                self._final_masked_mse_loss, var_list=self._trainable_vars, global_step=global_step
            )
            self._session.run(tf.variables_initializer(optimizer.variables()))

        return self._masked_mse_train_op

    def gen_fit_masked_mse(self, optimizer, epochs=1, iterations=10, global_step=None):
        """
        Method for training the model.

        Parameters
        ----------
        optimizer : tensorflow optimizer
            Model uses tensorflow optimizers in order train itself.
        epochs : int
            Number of epochs.
        iterations : int
            Defines how long one epoch is. One operation is a forward pass
            using one batch.
        global_step
            Please refer to TensorFlow documentation about global step for more info.

        Returns
        -------
        python dictionary
            Dictionary with all testing data(train error, train cost, test error, test cost)
            for each test period.
        """
        assert (optimizer is not None)
        assert (self._session is not None)

        train_op = self._minimize_masked_mse_loss(optimizer, global_step)

        mse_losses = []
        iterator = None
        try:
            for i in range(epochs):
                mse_loss = 0
                iterator = tqdm(range(iterations))

                for j in iterator:
                    batch_mse_loss, _ = self._session.run(
                        [self._final_masked_mse_loss, train_op], )
                    # Use exponential decay for calculating loss and error
                    mse_loss = moving_average(mse_loss, batch_mse_loss, j)

                mse_losses.append(mse_loss)

                print_train_info(i, (MASKED_MSE_LOSS, mse_loss))
        except Exception as ex:
            print(ex)
            print('type of error is ', type(ex))
        finally:
            if iterator is not None:
                iterator.close()
            return {MASKED_MSE_LOSS: mse_losses}


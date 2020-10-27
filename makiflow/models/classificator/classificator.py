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

from __future__ import absolute_import

import tensorflow as tf
import numpy as np
from tqdm import tqdm
from makiflow.models.classificator.utils import error_rate, sparse_cross_entropy
from copy import copy
import json
from makiflow.core import MakiTensor, MakiModel, MakiBuilder
from makiflow.layers import InputLayer
from makiflow.models.classificator.core.classificator_interface import ClassificatorInterface

EPSILON = np.float32(1e-37)


class CParams:
    INPUT_MT = 'input_mt'
    OUTPUT_MT = 'output_mt'
    NAME = 'name'


class Classificator(ClassificatorInterface):
    @staticmethod
    def from_json(path_to_model):
        """Creates and returns ConvModel from json.json file contains its architecture"""
        json_file = open(path_to_model)
        json_value = json_file.read()
        json_info = json.loads(json_value)

        output_tensor_name = json_info[MakiModel.MODEL_INFO][CParams.OUTPUT_MT]
        input_tensor_name = json_info[MakiModel.MODEL_INFO][CParams.INPUT_MT]
        model_name = json_info[MakiModel.MODEL_INFO][CParams.NAME]

        graph_info = json_info[MakiModel.GRAPH_INFO]

        inputs_outputs = MakiBuilder.restore_graph([output_tensor_name], graph_info)
        out_x = inputs_outputs[output_tensor_name]
        in_x = inputs_outputs[input_tensor_name]
        print('Model is restored!')
        return Classificator(in_x=in_x, out_x=out_x, name=model_name)

    def get_logits(self):
        return self._output

    def get_feed_dict_config(self) -> dict:
        return {
            self._input: 0
        }

    def __init__(self, in_x: InputLayer, out_x: MakiTensor, name='MakiClassificator'):
        self._input = in_x
        self._output = out_x
        graph_tensors = copy(out_x.get_previous_tensors())
        # Add output tensor to `graph_tensors` since it doesn't have it.
        # It is assumed that graph_tensors contains ALL THE TENSORS graph consists of.
        graph_tensors.update(out_x.get_self_pair())
        outputs = [out_x]
        inputs = [in_x]
        super().__init__(outputs, inputs)
        self.name = str(name)
        self._batch_sz = in_x.get_shape()[0]
        self._images = in_x.get_data_tensor()
        self._inference_out = out_x.get_data_tensor()
        self._softmax_out = tf.nn.softmax(self._inference_out)

    def _get_model_info(self):
        input_mt = self._inputs[0]
        output_mt = self._outputs[0]
        return {
            CParams.INPUT_MT: input_mt.get_name(),
            CParams.OUTPUT_MT: output_mt.get_name(),
            CParams.NAME: self.name
        }

    def evaluate(self, Xtest, Ytest):
        Xtest = Xtest.astype(np.float32)
        n_batches = Xtest.shape[0] // self._batch_sz

        test_cost = 0
        predictions = np.zeros(len(Xtest))
        for k in tqdm(range(n_batches)):
            Xtestbatch = Xtest[k * self._batch_sz:(k + 1) * self._batch_sz]
            Ytestbatch = Ytest[k * self._batch_sz:(k + 1) * self._batch_sz]
            Yish_test_done = self._session.run(self._softmax_out, feed_dict={self._images: Xtestbatch}) + EPSILON
            test_cost += sparse_cross_entropy(Yish_test_done, Ytestbatch)
            predictions[k * self._batch_sz:(k + 1) * self._batch_sz] = np.argmax(Yish_test_done, axis=-1)

        error_r = error_rate(predictions, Ytest)
        test_cost = test_cost / (len(Xtest) // self._batch_sz)
        return error_r, test_cost

    def predict(self, Xtest, use_softmax=True):
        if use_softmax:
            out = self._softmax_out
        else:
            out = self._inference_out
        n_batches = len(Xtest) // self._batch_sz

        predictions = []
        for i in tqdm(range(n_batches)):
            Xbatch = Xtest[i * self._batch_sz:(i + 1) * self._batch_sz]
            predictions += [self._session.run(out, feed_dict={self._images: Xbatch})]
        if len(predictions) > 1:
            return np.stack(predictions, axis=0)
        else:
            return predictions[0]


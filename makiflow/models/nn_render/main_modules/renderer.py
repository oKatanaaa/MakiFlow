import tensorflow as tf
from makiflow.base.maki_entities import MakiModel, MakiTensor
from makiflow.generators.nn_render import NNRIterator


class NeuralRenderBasis(MakiModel):
    def __init__(self, input_l, output, sampled_texture: MakiTensor, name):
        self.name = str(name)
        graph_tensors = output.get_previous_tensors()
        graph_tensors.update(output.get_self_pair())
        super().__init__(graph_tensors, outputs=[output], inputs=[input_l])
        self._sampled_texture = sampled_texture

        self._training_vars_are_ready = False
        self._learn_rgb_texture = False
        self._generator = None

    def predict(self, x):
        return self._session.run(
            self._output_data_tensors[0],
            feed_dict={self._input_data_tensors[0]: x}
        )

    def _get_model_info(self):
        return {
            'name': self.name,
            'input_s': self._inputs[0].get_name(),
            'output': self._outputs[0].get_name()
        }

    # ------------------------------------------------------------------------------------------------------------------
    # ----------------------------------------------------------SETTING UP TRAINING-------------------------------------

    def _prepare_training_vars(self):
        if not self._set_for_training:
            super()._setup_for_training()
        # VARIABLES PREPARATION
        out_shape = self._outputs[0].get_shape()
        self._out_h = out_shape[1]
        self._out_w = out_shape[2]
        self._batch_sz = out_shape[0]

        self._uv_maps = self._input_data_tensors[0]
        if self._generator is not None:
            self._images = self._generator.get_iterator()[NNRIterator.IMAGE]
        else:
            self._images = tf.placeholder(tf.float32, shape=out_shape, name='images')
        self._training_out = self._training_outputs[0]

        # OTHER PREPARATIONS
        if self._learn_rgb_texture:
            self._build_texture_loss()
        self._training_vars_are_ready = True

    def set_generator(self, generator):
        self._generator = generator

    # noinspection PyAttributeOutsideInit
    def set_learn_rgb_texture(self, scale):
        """
        Force the neural texture to learn RGB values in the first 3 channels.

        Parameters
        ----------
        scale : float
            Final loss will be derived in the following way:
            final_loss = objective + scale * texture_loss.
        """
        self._learn_rgb_texture = True
        self._texture_loss_scale = scale

    def _build_texture_loss(self):
        texture_tensor = self._sampled_texture.get_data_tensor()
        # [batch_size, height, width, channels]
        sampled_rgb_channels = texture_tensor[:, :, :, :3]
        diff = tf.abs(sampled_rgb_channels - self._images)
        self._texture_loss = tf.reduce_mean(diff)

    def _build_final_loss(self, custom_loss):
        # Override the method for the later ease of loss building
        if self._learn_rgb_texture:
            custom_loss = custom_loss + self._texture_loss * self._texture_loss_scale
        loss = super()._build_final_loss(custom_loss)
        return loss




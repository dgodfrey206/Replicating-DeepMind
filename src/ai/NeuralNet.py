"""

NeuralNet class creates a neural network.

"""

from convnet import *
import numpy as np
import time
from collections import OrderedDict

class SimpleDataProvider:
    dims = None

    def __init__(self, data_dir, batch_range=None, init_epoch=1, init_batchnum=None, dp_params=None, test=False):
        pass

    def get_data_dims(self, idx=0):
        assert self.dims is not None
        assert idx >= 0 and idx < len(self.dims)
        return self.dims[idx]

    def advance_batch(self):
        pass

class NeuralNet(ConvNet):

    def __init__(self, nr_inputs, nr_outputs, layers_file, params_file, output_layer_name):
        """
        Initialize a NeuralNet

        @param nr_inputs: number of inputs in data layer
        @param nr_outputs: number of target values in another data layer
        @param layers_file: path to layers file
        @param params_file: path to params file
        @param output_layer_name: name of the output layer
        """

        # Save data parameters
        self.nr_inputs = nr_inputs
        self.nr_outputs = nr_outputs
        SimpleDataProvider.dims = (nr_inputs, nr_outputs)

        # Save layer parameters
        self.layers_file = layers_file
        self.params_file = params_file
        self.output_layer_name = output_layer_name
        
        # Initialise ConvNet, including self.libmodel
        op = NeuralNet.get_options_parser()
        op, load_dic = IGPUModel.parse_options(op)
        ConvNet.__init__(self, op, load_dic)

    def train(self, inputs, outputs):
        """
        Train neural net with inputs and outputs.

        @param inputs: NxM numpy.ndarray, where N is number of inputs and M is batch size
        @param outputs: KxM numpy.ndarray, where K is number of outputs and M is batch size
        @return cost?
        """

        assert inputs.shape[0] == self.nr_inputs
        assert outputs.shape[0] == self.nr_outputs
        assert inputs.shape[1] == outputs.shape[1]

        # start training in GPU
        self.libmodel.startBatch([inputs, outputs], 1, False) # second parameter is 'progress', third parameter means 'only test, don't train'
        # wait until processing has finished
        cost = self.libmodel.finishBatch()
        # return cost (error)
        return cost

    def predict(self, inputs):
        """
        Predict neural network output layer activations for input.

        @param inputs: NxM numpy.ndarray, where N is number of inputs and M is batch size
        """
        assert inputs.shape[0] == self.nr_inputs

        batch_size = inputs.shape[1]
        outputs = np.zeros((batch_size, self.nr_outputs), dtype=np.float32)

        # start feed-forward pass in GPU
        self.libmodel.startFeatureWriter([inputs, outputs.transpose().copy()], [outputs], [self.output_layer_name])
        # wait until processing has finished
        self.libmodel.finishBatch()

        # now activations of output layer should be in 'outputs'
        return outputs

    def get_weight_stats(self):
        # copy weights from GPU to CPU memory
        self.sync_with_host()
        wscales = OrderedDict()
        for name,val in sorted(self.layers.items(), key=lambda x: x[1]['id']): # This is kind of hacky but will do for now.
            l = self.layers[name]
            if 'weights' in l:
                wscales[l['name'], 'biases'] = (n.mean(n.abs(l['biases'])), n.mean(n.abs(l['biasesInc'])))
                for i,(w,wi) in enumerate(zip(l['weights'],l['weightsInc'])):
                    wscales[l['name'], 'weights' + str(i)] = (n.mean(n.abs(w)), n.mean(n.abs(wi)))
        return wscales

    def save_network(self, epoch):
        self.epoch = epoch
        self.batchnum = 1
        self.sync_with_host()
        self.save_state().join()

    @classmethod
    def get_options_parser(cls):
        op = ConvNet.get_options_parser()
        #op.delete_option("train_batch_range")
        #op.delete_option("test_batch_range")
        #op.delete_option("dp_type")
        #op.delete_option("data_path")
        op.options["train_batch_range"].default="0"
        op.options["test_batch_range"].default="0"
        op.options["dp_type"].default="image"
        op.options["data_path"].default="/storage/hpc_kristjan/cuda-convnet4" # TODO: remove this
        op.options["layer_def"].default="ai/deepmind-layers.cfg"
        op.options["layer_params"].default="ai/deepmind-params.cfg"
        #op.options["save_path"].default="."
        #op.options["gpu"].default="0"
        op.options["dp_type"].default="simple"
        op.options["minibatch_size"].default = 32
 
        DataProvider.register_data_provider('simple', 'Simple data provider', SimpleDataProvider)

        return op

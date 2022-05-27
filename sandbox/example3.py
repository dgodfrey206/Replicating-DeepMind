


"""
First test using convolution
"""

import theano
import theano.tensor as T
import numpy as np
from theano.tensor.nnet import conv
# import theano.printing as tprint
import chessboard

def shared_dataset(data_xy):
    """
    Transform data into theano.shared. This is important for parallelising computations later
    """
    data_x, data_y = data_xy
    shared_x = theano.shared(np.asarray(data_x, dtype=theano.config.floatX))
    shared_y = theano.shared(np.asarray(data_y, dtype=theano.config.floatX))
    return shared_x, shared_y


class HiddenLayer:
    """
    Implements hidden layer of
    """

    def __init__(self, input, n_in, n_nodes):
        self.input = input

        W_bound = np.sqrt(6. /(n_in+n_nodes))
        #: Weight matrix (n_in x n_nodes)
        W_values = np.asarray(np.random.uniform(high=W_bound, low=-W_bound, size=(n_in, n_nodes)), dtype=theano.config.floatX)
        self.W = theano.shared(value=W_values, name='W', borrow=True)

        #: Bias term
        b_values = np.zeros((n_nodes,), dtype=theano.config.floatX)
        self.b = theano.shared(value=b_values, name='b', borrow=True)

        #: Output is just the weighted sum of activations
        self.output = T.dot(input, self.W) + self.b

        #all the variables that can change during learning
        self.params = [self.W, self.b]


class OutputLayer:
    """
    Implement last layer of the network. Output values of this layer are the results of the computation.
    """

    def __init__(self, input_from_previous_layer, n_in, n_nodes):

        self.input=input_from_previous_layer
        #: Weight matrix (n_in x n_nodes)
        W_bound = -np.sqrt(6. / (n_in + n_nodes))
        W_values = np.asarray(np.random.uniform(high=W_bound, low=-W_bound, size=(n_in, n_nodes)), dtype=theano.config.floatX)
        self.W = theano.shared(value=W_values, name='W', borrow=True)

        #: Bias term
        b_values = np.zeros((n_nodes,), dtype=theano.config.floatX)
        self.b = theano.shared(value=b_values, name='b', borrow=True)

        #output using linear rectifier
        self.threshold = 0
        lin_output = T.dot(input_from_previous_layer, self.W) + self.b
        above_threshold = lin_output > self.threshold
        self.output = above_threshold * (lin_output - self.threshold)

        #all the variables that can change during learning
        self.params = [self.W, self.b]

    def errors(self, y):
        """ return the error made in predicting the output value
        :type y: theano.tensor.TensorType
        :param y: corresponds to a vector that gives for each example the
        correct label
        """

        # check if y has same dimension of output
        if y.ndim != self.output.ndim:
            raise TypeError('y should have the same shape as self.output', ('y', y.type, 'output', self.output.type))

        return np.abs(T.mean(self.output-y))


class ConvolutionalLayer(object):
    """Pool Layer of a convolutional network """

    def __init__(self, input_images, filter_shape, image_shape, stride=4):
        """
        Allocate a LeNetConvPoolLayer with shared variable internal parameters.

        :type input: theano.tensor.dtensor4
        :param input: symbolic image tensor, of shape image_shape

        :type filter_shape: tuple or list of length 4
        :param filter_shape: (number of filters, num input feature maps,
                              filter height,filter width)

        :type image_shape: tuple or list of length 4
        :param image_shape: (batch size, num input feature maps,
                             image height, image width)

        :type poolsize: tuple or list of length 2
        :param poolsize: the downsampling (pooling) factor (#rows,#cols)
        """

        assert image_shape[1] == filter_shape[1]
        self.input = input

        # there are "num input feature maps * filter height * filter width"
        # inputs to each hidden unit
        self.fan_in = np.prod(filter_shape[1:])

        # number of nodes in our layer is nr_of_filters*( (image_size-filter_size)/stride))**2
        feature_map_size=1+(image_shape[2]-filter_shape[2])/stride
        self.fan_out = (filter_shape[0] * feature_map_size * feature_map_size)


        #we need to define the interval at which we initialize the weights. We use formula from example
        W_bound = np.sqrt(6. / (self.fan_in + self.fan_out))

        # initialize weights with random weights
        self.W = theano.shared(np.asarray(np.random.uniform(high=W_bound, low=-W_bound, size=filter_shape), dtype=theano.config.floatX),
                               borrow=True)

        # the bias is a 1D tensor -- one bias per output feature map
        b_values = np.zeros((filter_shape[0],), dtype=theano.config.floatX)
        self.b = theano.shared(value=b_values, borrow=True)

        # convolve input feature maps with filters
        convolution_output = conv.conv2d(input=input_images, filters=self.W,
                filter_shape=filter_shape, image_shape=image_shape, subsample=(stride , stride))

        # add the bias term. Since the bias is a vector (1D array), we first
        # reshape it to a tensor of shape (1,n_filters,1,1). Each bias will
        # thus be broadcasted across mini-batches and feature map
        # width & height
        self.threshold = 0
        activation = convolution_output + self.b.dimshuffle('x', 0, 'x', 'x')
        #above_threshold = activation > self.threshold
        #self.output = above_threshold * (activation - self.threshold)
        self.output=activation
        # store parameters of this layer
        self.params = [self.W, self.b]


class MLP:
    """
    Class which implements the classification algorithm (neural network in our case)
    """
    def __init__(self, input, input_shape, filter_shapes, strides, n_hidden, n_out):


        #: Convolutional layer
        self.conv_layer = ConvolutionalLayer(input, filter_shapes[0], input_shape, strides[0])

        flattened_input=self.conv_layer.output.flatten(2)

        #: Hidden layer implements summation
        self.hidden_layer = HiddenLayer(flattened_input, self.conv_layer.fan_out, n_hidden)

        #: Output layer implements summations and rectifier non-linearity
        self.output_layer = OutputLayer(self.hidden_layer.output, n_hidden, n_out)




        # L1 norm ; one regularization option is to enforce L1 norm to
        # be small
        self.L1 = abs(self.hidden_layer.W).sum() \
                + abs(self.output_layer.W).sum() \
                + abs(self.conv_layer.W).sum()

        # square of L2 norm ; one regularization option is to enforce
        # square of L2 norm to be small
        self.L2_sqr = (self.hidden_layer.W ** 2).sum() \
                    + (self.output_layer.W ** 2).sum() \
                    + (self.conv_layer.W ** 2).sum()

        self.params = self.hidden_layer.params + self.output_layer.params + self.conv_layer.params


def main():

    #: Define data sets
    train_set = (np.array([chessboard.make_chessboard(8), chessboard.make_chessboard(2)]),
                 np.array([[[10.0]], [[20.0]]]))


    # Transform them to theano.shared
    train_set_x, train_set_y = shared_dataset(train_set)

    #test_set_x, test_set_y = shared_dataset(test_set)

    # This is how you can print weird theano stuff
    print train_set_x.eval()
    print train_set_y.eval()

    # Define some structures to store training data and labels
    x = T.matrix('x')
    y = T.matrix('y')
    index = T.lscalar()

    input_tensor=x.reshape((1,1,84,84))

    # Define the classification algorithm
    classifier = MLP(input=input_tensor, input_shape=[1, 1, 84, 84], filter_shapes=[[16, 1, 8, 8]], strides=[4], n_hidden=40, n_out=1)

    #define the cost function using l1 and l2 regularization terms:
    cost = classifier.output_layer.errors(y) \
        + 0.0 * classifier.L1 \
        + 0.0 * classifier.L2_sqr

    print type(cost)

    # Calculate the derivatives by each existing parameter
    grads = T.grad(cost, classifier.params)

    # Define how much we need to change the parameter values
    learning_rate = 0.0001
    updates = []
    for param_i, gparam_i in zip(classifier.params, grads):
        updates.append((param_i, param_i - learning_rate * gparam_i))

    #print updates

    # Train model is a theano.function type object that performs updates on parameter values
    train_model = theano.function(inputs=[index], outputs=cost,
            updates=updates,
            givens={
                x: train_set_x[index],
                y: train_set_y[index]})



    # We construct an object of type theano.function, which we call test_model
    test_model = theano.function(
        inputs=[index],
        outputs=[classifier.conv_layer.W, classifier.hidden_layer.b, classifier.output_layer.W, classifier.output_layer.b, classifier.output_layer.output, cost],
        givens={
            x: train_set_x[index],
            y: train_set_y[index]
            })

    n_train_points = train_set_x.get_value(borrow=True).shape[0]
    print "nr of training points is ", n_train_points

    for i in range(n_train_points):
        result = test_model(i)
        print "we calculated something: ", result


    #lets train some iterations:

    for i in range(10000):
        cost = train_model(0)
        cost = train_model(1)

        result = test_model(0)

        print "test0: ", result[-3:]
        result = test_model(1)
        print "test1: ", result[-3:]


    #for i in range(n_train_points):
    #    result = test_model(i)
    #    print "we calculated something: ", result

if __name__ == '__main__':
    main()
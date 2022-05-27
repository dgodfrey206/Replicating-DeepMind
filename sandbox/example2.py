"""
Minimal example of using theano and neural network and gradient decent
"""

import theano
import theano.tensor as T
import numpy as np
# import theano.printing as tprint


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

        #: Weight matrix (n_in x n_nodes)
        W_values = np.asarray(np.ones((n_in, n_nodes)) * 2, dtype=theano.config.floatX)
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
        #: Weight matrix (n_in x n_nodes)
        W_values = np.asarray(np.ones((n_in, n_nodes)) * 2, dtype=theano.config.floatX)
        self.W = theano.shared(value=W_values, name='W', borrow=True)

        #: Bias term
        b_values = np.zeros((n_nodes,), dtype=theano.config.floatX)
        self.b = theano.shared(value=b_values, name='b', borrow=True)

        #output using linear rectifier
        self.threshold = 1
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


class MLP:
    """
    Class which implements the classification algorithm (neural network in our case)
    """
    def __init__(self, input, n_in, n_hidden, n_out):

        #: Hidden layer implements summation
        self.hidden_layer = HiddenLayer(input, n_in, n_hidden)

        #: Output layer implements summations and rectifier non-linearity
        self.output_layer = OutputLayer(self.hidden_layer.output, n_hidden, n_out)




        # L1 norm ; one regularization option is to enforce L1 norm to
        # be small
        self.L1 = abs(self.hidden_layer.W).sum() \
                + abs(self.output_layer.W).sum()

        # square of L2 norm ; one regularization option is to enforce
        # square of L2 norm to be small
        self.L2_sqr = (self.hidden_layer.W ** 2).sum() \
                    + (self.output_layer.W ** 2).sum()

        self.params = self.hidden_layer.params + self.output_layer.params


def main():

    #: Define data sets
    #train_set = (np.array([[1, 1], [1, 0], [0, 1], [0, 0]]), np.array([1, 0, 0, 0]))
    train_set = (np.array([[[0, 0], [0, 1], [1, 1], [1, 0]], [[0, 0], [0, 1], [1, 1], [1, 0]]]), np.array([[[0],[0], [1], [0]], [[0],[0], [1], [0]]]))
    test_set = (np.array([[0, 0], [1, 0]]), np.array([0, 0]))

    # Transform them to theano.shared
    train_set_x, train_set_y = shared_dataset(train_set)

    test_set_x, test_set_y = shared_dataset(test_set)

    # This is how you can print weird theano stuff
    print train_set_x.eval()
    print train_set_y.eval()

    # Define some structures to store training data and labels
    x = T.matrix('x')
    y = T.matrix('y')
    index = T.lscalar()


    # Define the classification algorithm
    classifier = MLP(input=x, n_in=2, n_hidden=1, n_out=1)

    #define the cost function using l1 and l2 regularization terms:
    cost = classifier.output_layer.errors(y) \
        + 0.0 * classifier.L1 \
        + 0.0 * classifier.L2_sqr

    # print type(cost)

    # Calculate the derivatives by each existing parameter
    gparams = []
    for param in classifier.params:
        gparam = T.grad(cost, param)
        gparams.append(gparam)

    # Define how much we need to change the parameter values
    learning_rate = 0.02
    updates = []
    for param, gparam in zip(classifier.params, gparams):
        updates.append((param, param - learning_rate * gparam))

    print updates

    # Train model is a theano.function type object that performs updates on parameter values
    train_model = theano.function(inputs=[index], outputs=cost,
            updates=updates,
            givens={
                x: train_set_x[index],
                y: train_set_y[index]})

    # We construct an object of type theano.function, which we call test_model
    test_model = theano.function(
        inputs=[index],
        outputs=[classifier.hidden_layer.input, classifier.output_layer.output, cost, classifier.hidden_layer.W,
                 classifier.hidden_layer.b, classifier.output_layer.W, classifier.output_layer.b],
        givens={
            x: train_set_x[index],
            y: train_set_y[index]})

    n_train_points = train_set_x.get_value(borrow=True).shape[0]
    print "nr of training points is ", n_train_points

    for i in range(n_train_points):
        result = test_model(i)
        print "we calculated something: ", result

    # lets train some iterations:
    for iteration in range(1000):
        cost = train_model(0)

    for i in range(n_train_points):
        result = test_model(i)
        print "we calculated something: ", result

if __name__ == '__main__':
    main()
"""
This file defines classes that control who ObservationMetaData describes
its field of view (i.e. is it a box in RA, Dec, is it a circle in RA, Dec....?)
"""

#Hopefully it will be extensible so that we can add different shapes in the
#future

import numpy as np

class SpatialBoundsMetaClass(type):
    """
    Meta class for fieldOfView.  This class builds a registry of all
    valid fields of view so that fields can be instantiated from just a
    dictionary key.
    """

    #Largely this is being copied from the DBObjectMeta class in
    #dbConnection.py

    def __init__(cls, name, bases, dct):
        if not hasattr(cls,'SBregistry'):
            cls.SBregistry={}
        else:
            cls.SBregistry[cls.boundType] = cls

        return super(SpatialBoundsMetaClass, cls).__init__(name,bases,dct)

class SpatialBounds(object):
    """
    Classes inheriting from this class define spatial bounds on the objects
    contained within a catalog.  They also translate those bounds into
    constraints on SQL queries made by the query_columns method in
    CatalogDBobject (see dbConnnection.py)

    Daughter classes of this class need the following:

    self.boundType = a string by which the class is identified in the
    registry of FieldOfView classes

    __init__() that accepts (in this order) RA, Dec, and characteristic
    length.  Init should then construct the parameters defining the bound
    however is appropriate (e.g. setting self.RAmax and self.RAmin for a box)

    to_SQL() = a method that accepts RAcolname and DECcolname (strings denoting
    the names of the database columns containing RA and DEc) and which returns
    a string that characterizes the bound as an SQL 'WHERE' statement.
    """

    __metaclass__ = SpatialBoundsMetaClass

    def __init__(self, *args):
        """
        Accepts a center point and a characteristic length defining the extent of
        the bounds

        @param[in] ra is the center RA in degrees

        @param[in] dec is the center Dec in degress

        @param[in] length is either a single characteristic length (in degrees)
        or a list of characteristic lengths defining the shape of the bound
        """

        raise NotImplementedError()

    def to_SQL(self, *args):
        """
        Accepts the names of the columns referring to RA and Dec in the database.
        Uses the stored RA, Dec, and length for this object to return an SQL
        query that only selects the region of RA and Dec desired

        @param[in] RAname a string; the name of the RA column in the database

        @param[in] DECname a string; the name of the Dec column in the database

        @returns a string; an SQL query that only selects the desired region in RA, Dec
        """

        raise NotImplementedError()

    @classmethod
    def getSpatialBounds(self, name, *args, **kwargs):
        if name in self.SBregistry:
            return self.SBregistry[name](*args, **kwargs)
        else:
            raise RuntimeError("There is no SpatialBounds class keyed to %s" % name)

class CircleBounds(SpatialBounds):

    boundType = 'circle'

    def __init__(self, ra, dec, radius):
        self.RA = ra
        self.DEC = dec
        self.radius = radius

    def to_SQL(self, RAname, DECname):

        if self.DEC != 90.0 and self.DEC != -90.0:
            RAmax = self.RA + \
            360.0 * np.arcsin(np.sin(0.5*np.radians(self.radius)) / np.cos(np.radians(self.DEC)))/np.pi
            RAmin = self.RA - \
            360.0 * np.arcsin(np.sin(0.5*np.radians(self.radius)) / np.cos(np.radians(self.DEC)))/np.pi
        else:
           #just in case, for some reason, we are looking at the poles
           RAmax = 360.0
           RAmin = 0.0

        DECmax = self.DEC + self.radius
        DECmin = self.DEC - self.radius

        #initially demand that all objects are within a box containing the circle
        #set from the DEC1=DEC2 and RA1=RA2 limits of the haversine function
        bound = ("%s between %f and %f and %s between %f and %f "
                     % (RAname, RAmin, RAmax, DECname, DECmin, DECmax))

        #then use the Haversine function to constrain the angular distance form boresite to be within
        #the desired radius.  See http://en.wikipedia.org/wiki/Haversine_formula
        bound = bound + ("and 2 * ASIN(SQRT( POWER(SIN(0.5*(%s - %s) * PI() / 180.0),2)" % (DECname,self.DEC))
        bound = bound + ("+ COS(%s * PI() / 180.0) * COS(%s * PI() / 180.0) " % (DECname, self.DEC))
        bound = bound + ("* POWER(SIN(0.5 * (%s - %s) * PI() / 180.0),2)))" % (RAname, self.RA))
        bound = bound + (" < %s " % (self.radius*np.pi/180.0))

        return bound

class BoxBounds(SpatialBounds):

    boundType = 'box'

    def __init__(self, ra, dec, length):
        self.RA = ra
        self.DEC = dec

        if isinstance(length, float):
            self.RAmin = self.RA - length
            self.RAmax = self.RA + length
            self.DECmin = self.DEC - length
            self.DECmax = self.DEC + length
        elif len(length)==1:
            self.RAmin = self.RA - length[0]
            self.RAmax = self.RA + length[0]
            self.DECmin = self.DEC - length[0]
            self.DECmax = self.DEC + length[0]
        else:
            try:
                self.RAmin = self.RA - length[0]
                self.RAmax = self.RA + length[0]
                self.DECmin = self.DEC - length[1]
                self.DECmax = self.DEC + length[1]
            except:
                raise RuntimeError("BoxBounds is unsure how to handle length %s " % str(length))

        self.RAmin %= 360.0
        self.RAmax %= 360.0

    def to_SQL(self, RAname, DECname):
        #KSK:  I don't know exactly what we do here.  This is in code, but operating
        #on a database is it less confusing to work in degrees or radians?
        #(RAmin, RAmax, DECmin, DECmax) = map(math.radians,
        #                                     (RAmin, RAmax, DECmin, DECmax))

        #Special case where the whole region is selected
        if self.RAmin < 0 and self.RAmax > 360.:
            bound = "%s between %f and %f" % (DECname, self.DECmin, self.DECmax)
            return bound

        if self.RAmin > self.RAmax:
            # XXX is this right?  It seems strange.
            bound = ("%s not between %f and %f and %s between %f and %f"
                     % (RAname, self.RAmax, self.RAmin,
                        DECname, self.DECmin, self.DECmax))
        else:
            bound = ("%s between %f and %f and %s between %f and %f"
                     % (RAname, self.RAmin, self.RAmax, DECname, self.DECmin, self.DECmax))

        return bound



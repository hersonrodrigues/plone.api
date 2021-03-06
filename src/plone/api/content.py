""" Module that provides functionality for content manipulation """

from App.config import getConfiguration
from plone.app.uuid.utils import uuidToObject
from Products.Archetypes.interfaces.base import IBaseObject
from Products.CMFPlone.utils import getToolByName
from zope.app.component.hooks import getSite
from zope.app.container.interfaces import INameChooser
from zope.component import getMultiAdapter

import random
import transaction


def create(container=None,
           type=None,
           id=None,
           title=None,
           strict=True,
           **kwargs):
    """Create a new content item.

    :param container: [required] Container object in which to create the new
        object.
    :type container: Folderish content object
    :param type: [required] Type of the object.
    :type type: string
    :param id: Id of the object.  If the id conflicts with another object in
        the container, a suffix will be added to the new object's id. If no id
        is provided, automatically generate one from the title. If there is no
        id or title provided, raise a ValueError.
    :type id: string
    :param title: Title of the object. If no title is provided, use id as
        the title.
    :type title: string
    :param strict: When True, the given id will be enforced. If the id is
        conflicting with another object in the target container, raise a
        KeyError. When False, ``create`` creates a new, non-conflicting id.
    :type strict: boolean
    :returns: Content object

    :Example: :ref:`content_create_example`
    """
    if not container:
        raise ValueError('The ``container`` attribute is required.')

    if not type:
        raise ValueError('The ``type`` attribute is required.')

    if not id and not title:
        raise ValueError('You have to provide either the ``id`` or the '
                         '``title`` attribute')

    # Create a temporary id if the id is not given
    content_id = strict and id or str(random.randint(0, 99999999))

    if title:
        kwargs['title'] = title

    container.invokeFactory(type, content_id, **kwargs)
    content = container[content_id]

    # Archetypes specific code
    if IBaseObject.providedBy(content):
        # Will finish Archetypes content item creation process,
        # rename-after-creation and such
        content.processForm()

    if not id or (not strict and id):
        # Create a new id from title
        chooser = INameChooser(container)
        derived_id = id or title
        new_id = chooser.chooseName(derived_id, content)
        # kacee: we must do a partial commit, else the renaming fails because
        # the object isn't in the zodb.
        # Thus if it is not in zodb, there's nothing to move. We should
        # choose a correct id when
        # the object is created.
        # maurits: tests run fine without this though.
        transaction.savepoint(optimistic=True)
        content.aq_parent.manage_renameObject(content_id, new_id)

    return content


def get(path=None, UID=None):
    """Get an object.

    :param path: Path to the object we want to get, relative to
        the portal root.
    :type path: string
    :param UID: UID of the object we want to get.
    :type UID: string
    :returns: Content object
    :Example: :ref:`content_get_example`
    """
    if path and UID:
        raise ValueError('When getting an object combining path and UID '
                         'attribute is not allowed')

    if not path and not UID:
        raise ValueError('When getting an object path or UID attribute is '
                         'required')

    if path:
        site = getSite()
        site_id = site.getId()
        if not path.startswith('/{0}'.format(site_id)):
            path = '/{0}{1}'.format(site_id, path)

        try:
            return site.restrictedTraverse(path)
        except KeyError:
            return None  # When no object is found don't raise an error

    elif UID:
        return uuidToObject(UID)


def move(source=None, target=None, id=None, strict=True):
    """Move the object to the target container.

    :param source: [required] Object that we want to move.
    :type source: Content object
    :param target: Target container to which the source object will
        be moved. If no target is specified, the source object's container will
        be used as a target, effectively making this operation a rename
        (:ref:`rename_content_example`).
    :type target: Folderish content object
    :param id: Pass this parameter if you want to change the id of the moved
        object on the target location. If the new id conflicts with another
        object in the target container, a suffix will be added to the moved
        object's id.
    :type id: string
    :param strict: When True, the given id will be enforced. If the id is
        conflicting with another object in the target container, raise a
        KeyError. When False, move creates a new, non-conflicting id.
    :type strict: boolean
    :Example: :ref:`content_move_example`
    """
    if not source:
        raise ValueError

    if not target and not id:
        raise ValueError

    source_id = source.getId()

    # If no target is given the object is probably renamed
    if target:
        target.manage_pasteObjects(source.manage_cutObjects(source_id))
    else:
        target = source

    if id:
        if strict:
            new_id = id
        else:
            chooser = INameChooser(target)
            new_id = chooser.chooseName(id, source)

        target.manage_renameObject(source_id, new_id)


def copy(source=None, target=None, id=None, strict=True):
    """Copy the object to the target container.

    :param source: [required] Object that we want to copy.
    :type source: Content object
    :param target: Target container to which the source object will
        be moved. If no target is specified, the source object's container will
        be used as a target.
    :type target: Folderish content object
    :param id: Id of the copied object on the target location. If no id is
        provided, the copied object will have the same id as the source object
        - however, if the new object's id conflicts with another object in the
        target container, a suffix will be added to the new object's id.
    :type id: string
    :returns: Content object that was created in the target location
    :param strict: When True, the given id will be enforced. If the id is
        conflicting with another object in the target container, raise a
        KeyError. When False, ``copy`` creates a new, non-conflicting id.
    :type param: boolean
    :Example: :ref:`content_copy_example`
    """
    if not source:
        raise ValueError

    if not target and not id:
        raise ValueError

    source_id = source.getId()
    target.manage_pasteObjects(source.manage_copyObjects(source_id))

    if id:
        if strict:
            new_id = id
        else:
            chooser = INameChooser(target)
            new_id = chooser.chooseName(id, source)

        target.manage_renameObject(source_id, new_id)


def delete(obj=None):
    """Delete the object.

    :param obj: [required] Object that we want to delete.
    :type obj: Content object
    :Example: :ref:`content_delete_example`
    """
    if not obj:
        raise ValueError

    obj.aq_parent.manage_delObjects([obj.getId()])


def get_state(obj=None):
    """Get the current workflow state of the object.

    :param obj: [required] Object that we want to get the state for.
    :type obj: Content object
    :returns: Object's current workflow state
    :rtype: string
    :Example: :ref:`content_get_state_example`
    """
    if not obj:
        raise ValueError

    workflow = getToolByName(getSite(), 'portal_workflow')
    return workflow.getInfoFor(obj, 'review_state')


def transition(obj=None, transition=None):
    """Perform a workflow transition for the object.

    :param obj: [required] Object for which we want to perform the workflow
        transition.
    :type obj: Content object
    :param transition: [required] Name of the workflow transition.
    :type transition: string
    :Example: :ref:`content_transition_example`
    """
    if not obj or not transition:
        raise ValueError

    workflow = getToolByName(getSite(), 'portal_workflow')
    workflow.doActionFor(obj, transition)


def get_view(name=None, context=None, request=None):
    """Get a BrowserView object.

    :param name: [required] Name of the view.
    :type name: string
    :param context: [required] Context on which to get view.
    :type context: context object
    :param request: [required] Request on which to get view.
    :type request: request object
    :Example: :ref:`content_get_view_example`
    """
    if not name:
        raise ValueError

    if not context:
        raise ValueError

    if not request:
        raise ValueError

    # It happens sometimes that ACTUAL_URL is not set in tests. To be nice
    # and not throw strange errors, we set it to be the same as URL.
    # TODO: if/when we have api.env.test_mode() boolean in the future, use that
    config = getConfiguration()
    if config.dbtab.__module__ == 'plone.testing.z2':
        request['ACTUAL_URL'] = request['URL']

    return getMultiAdapter((context, request), name=name)
